"""Проверка сданной попытки LLM-судьёй по рубрике задачи.

1. Автотесты задачи прогоняются на итоговых файлах.
2. Судья получает материалы (тесты, файлы, журнал сессии) и по каждому критерию ставит
   «да / частично / нет» с дословной цитатой. Прогонов несколько, независимо друг от друга.
3. Постобработка: цитата ищется в материалах — не нашлась, критерий не засчитан;
   «частично» там, где оно не разрешено, считается «нет».
4. По каждому критерию итог — большинство прогонов (медиана: нет < частично < да).
   Баллы — сумма по критериям, грейд — высший порог, где хватает баллов и все обязательные критерии «да».
   Если прогоны дали разный грейд — засчитывается нижний.
"""

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bus import EventBus
from app.db import utcnow
from app.llm.gateway import Gateway
from app.llm.types import Message, Priority
from app.models import Attempt, CriterionVerdict, Grading, SessionEvent
from app.prompts import JUDGE_PROMPT_VERSION, JUDGE_SYSTEM, judge_user_message
from app.sandbox import RunResult, Runner
from app.service import Conflict, NotFound, event_view
from app.tasks import GRADE_ORDER, Rubric, Task

log = logging.getLogger(__name__)

VERDICT_RANK = {"no": 0, "partial": 1, "yes": 2}
_MAX_FILE_CHARS = 20_000
_MAX_DIFF_LINES = 80
_MAX_MESSAGE_CHARS = 2_000
_MIN_QUOTE_CHARS = 6


class JudgeVerdict(BaseModel):
    criterion_id: str
    verdict: Literal["yes", "partial", "no"]
    evidence: str = ""
    comment: str = ""


class JudgeOutput(BaseModel):
    verdicts: list[JudgeVerdict]


# --- материалы для судьи ---


def render_evidence(files: dict[str, str], events: list[SessionEvent], started_at: datetime, tests: RunResult | None) -> str:
    """Всё, из чего судья может цитировать. Условие задачи и критерии сюда не входят —
    цитата из них ничего не доказывает."""
    if tests is None:
        tests_block = "В задаче нет автотестов."
    else:
        tests_block = ("Прошли. " if tests.passed else "Не прошли. ") + tests.summary(6000)
    files_block = "\n\n".join(f"=== {path} ===\n{_cut(content, _MAX_FILE_CHARS)}" for path, content in sorted(files.items()))
    log_lines = [line for ev in events if (line := _render_event(ev, started_at))]
    return (
        f"<исходные_тесты_задачи_на_решении_кандидата>\n{tests_block}\n</исходные_тесты_задачи_на_решении_кандидата>\n\n"
        f"<итоговые_файлы>\n{files_block or 'Файлов нет.'}\n</итоговые_файлы>\n\n"
        "<журнал_сессии>\n" + "\n".join(log_lines) + "\n</журнал_сессии>"
    )


def _render_event(ev: SessionEvent, started_at: datetime) -> str | None:
    p = ev.payload
    seconds = max(0, int((ev.created_at - started_at).total_seconds()))
    t = f"[{seconds // 60:02d}:{seconds % 60:02d}]"
    match ev.type:
        case "attempt.started":
            return f"{t} Начало сессии"
        case "assistant.user_message":
            return f"{t} Кандидат → ассистенту: {_cut(p['text'], _MAX_MESSAGE_CHARS)}"
        case "assistant.message":
            return f"{t} Ассистент → кандидату: {_cut(p['text'], _MAX_MESSAGE_CHARS)}"
        case "assistant.tool":
            args = ", ".join(f"{k}={v}" for k, v in p.get("args", {}).items())
            return f"{t} Ассистент вызвал {p['tool']}({args})"
        case "assistant.error":
            return f"{t} Ошибка ассистента: {p['error']}"
        case "edit.proposed":
            return f"{t} Ассистент предложил правку #{p['edit_id']} в {p['path']}: {p.get('summary', '')}\n{_cut_lines(p.get('diff', ''))}"
        case "edit.accepted":
            return f"{t} Кандидат принял правку #{p['edit_id']} в {p['path']}"
        case "edit.rejected":
            reason = f": {p['reason']}" if p.get("reason") else ""
            return f"{t} Кандидат отклонил правку #{p['edit_id']} в {p['path']}{reason}"
        case "edit.stale":
            return f"{t} Правка #{p['edit_id']} устарела: файл {p['path']} изменился раньше"
        case "file.saved":
            return f"{t} Кандидат вручную изменил {p['path']}\n{_cut_lines(p.get('diff', ''))}"
        case "tests.run":
            who = "кандидат" if p.get("by") == "candidate" else "ассистент"
            return f"{t} Тесты запустил {who}: {'прошли' if p.get('passed') else 'не прошли'}"
        case "attempt.submitted":
            return f"{t} Кандидат сдал решение"
        case "attempt.expired":
            return f"{t} Время вышло, решение сдано автоматически"
    return None


def _cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "\n…[обрезано]"


def _cut_lines(text: str) -> str:
    lines = text.splitlines()
    return text if len(lines) <= _MAX_DIFF_LINES else "\n".join(lines[:_MAX_DIFF_LINES] + ["…[дифф обрезан]"])


# --- постобработка ---


_QUOTE_CHARS = str.maketrans({"«": '"', "»": '"', "“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "—": "-", "–": "-"})
_LOG_TIME = re.compile(r"\[\d{2}:\d{2}\]")
# Непрерывный совпавший кусок короче этого ничего не доказывает; длиннее второго — уже точно взят из материалов
_MIN_RUN = 20
_SURE_RUN = 40


def normalize(text: str) -> str:
    text = _LOG_TIME.sub(" ", text.translate(_QUOTE_CHARS))
    return re.sub(r"\s+", " ", text).strip().lower()


def evidence_found(quote: str, haystack: str) -> bool:
    """Цитата засчитывается, если она действительно взята из материалов, а не пересказана.

    Судья склеивает строки журнала, меняет кавычки, добавляет пару слов вокруг цитаты — на живом GigaChat
    точное совпадение срезало большую часть верных «да». Поэтому цитата режется на фрагменты
    (по многоточиям и переносам строк), и для каждого ищется длинный непрерывный совпадающий кусок.
    Засчитываем, если найденное покрывает большую часть цитаты или есть один бесспорно длинный кусок.
    haystack — уже нормализованный текст материалов."""
    fragments = [normalize(f).strip(" \"'`:;,.") for f in re.split(r"\.\.\.|…|\n", quote)]
    fragments = [f for f in fragments if len(f) >= _MIN_QUOTE_CHARS]
    if not fragments:
        return False
    runs = [_longest_run(f, haystack) for f in fragments]
    # короткий фрагмент засчитывается, только если найден целиком
    covered = sum(run for f, run in zip(fragments, runs) if run >= _MIN_RUN or run == len(f))
    return covered >= 0.6 * sum(len(f) for f in fragments) or max(runs) >= _SURE_RUN


def _longest_run(fragment: str, haystack: str) -> int:
    if fragment in haystack:
        return len(fragment)
    match = SequenceMatcher(None, haystack, fragment, autojunk=False).find_longest_match(0, len(haystack), 0, len(fragment))
    return match.size


def auto_verdicts(
    rubric: Rubric, tests: RunResult | None, events: list[SessionEvent] | None = None, started_at: datetime | None = None
) -> dict[str, dict[str, Any]]:
    """Критерии, которые засчитывает платформа без судьи: check=tests — по факту прогона автотестов,
    check=verified — по журналу действий кандидата."""
    out = {}
    for c in rubric.criteria:
        if c.check == "verified":
            out[c.id] = verified_by_journal(events or [], started_at)
            continue
        if c.check != "tests":
            continue
        passed = tests is not None and tests.passed
        last_line = (tests.summary().strip().splitlines() or [""])[-1] if tests else ""
        out[c.id] = {
            "verdict": "yes" if passed else "no",
            "counted": "yes" if passed else "no",
            "evidence": last_line if passed else "",
            "evidence_found": passed,
            "comment": "Автотесты на итоговой версии проходят" if passed else "Автотесты на итоговой версии не проходят",
        }
    return out


def verified_by_journal(events: list[SessionEvent], started_at: datetime | None) -> dict[str, Any]:
    """«Проверял работу ассистента» — по журналу, без судьи: отклонил правку ассистента, поправил принятую
    вручную или запустил тесты после принятой правки. Доказательство — строки журнала."""
    start = started_at or (events[0].created_at if events else datetime.min)
    line = lambda ev: (_render_event(ev, start) or "").splitlines()[0]
    accepted: dict[str, SessionEvent] = {}  # файл → последняя принятая правка в нём
    proof, comment = None, ""
    for ev in events:
        if ev.type == "edit.rejected":
            proof, comment = [line(ev)], "Отклонил предложение ассистента"
            break
        if ev.type == "edit.accepted":
            accepted[ev.payload.get("path", "")] = ev
        elif ev.type == "tests.run" and ev.payload.get("by") == "candidate" and accepted:
            last = max(accepted.values(), key=lambda e: e.id)
            proof, comment = [line(last), line(ev)], "После принятой правки ассистента запускал тесты"
            break
        elif ev.type == "file.saved" and ev.payload.get("path") in accepted:
            proof, comment = [line(accepted[ev.payload["path"]]), line(ev)], "Поправил принятую правку ассистента вручную"
            break
    if proof:
        return {"verdict": "yes", "counted": "yes", "evidence": "\n".join(proof), "evidence_found": True, "comment": comment}
    comment = "Принятые правки ассистента не проверял" if accepted else "Правки ассистента не принимал и не отклонял"
    return {"verdict": "no", "counted": "no", "evidence": "", "evidence_found": False, "comment": comment}


def evaluate_run(rubric: Rubric, output: JudgeOutput, haystack: str, auto: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Один прогон судьи → засчитанные вердикты, баллы и грейд. auto — вердикты, которые платформа ставит сама."""
    auto = auto or {}
    given = {}
    for v in output.verdicts:
        given.setdefault(v.criterion_id, v)
    verdicts = {}
    for c in rubric.criteria:
        if c.id in auto:
            verdicts[c.id] = dict(auto[c.id])
            continue
        v = given.get(c.id)
        if v is None:
            verdicts[c.id] = {"verdict": "no", "counted": "no", "evidence": "", "evidence_found": False, "comment": "Судья не дал вердикт"}
            continue
        found = v.verdict != "no" and evidence_found(v.evidence, haystack)
        counted = v.verdict
        if counted == "partial" and c.partial_points is None:
            counted = "no"
        if counted != "no" and not found:
            counted = "no"
        verdicts[c.id] = {
            "verdict": v.verdict,
            "counted": counted,
            "evidence": v.evidence,
            "evidence_found": found,
            "comment": v.comment,
        }
    counted = {cid: v["counted"] for cid, v in verdicts.items()}
    score = score_of(rubric, counted)
    score_100 = to_100(score, rubric.max_points)
    reached = reached_grades(rubric, counted, score_100)
    return {"verdicts": verdicts, "score": score, "score_100": score_100, "reached": reached, "grade": highest(reached)}


def score_of(rubric: Rubric, counted: dict[str, str]) -> int:
    total = 0
    for c in rubric.criteria:
        if counted[c.id] == "yes":
            total += c.points
        elif counted[c.id] == "partial":
            total += c.partial_points or 0
    return total


def to_100(score: int, max_points: int) -> int:
    """Балл по шкале 0–100, с округлением вверх. Целочисленно: 7 из 10 — ровно 70, без ошибок дробей."""
    return -(-100 * score // max_points) if max_points else 0


def reached_grades(rubric: Rubric, counted: dict[str, str], score_100: int) -> dict[str, bool]:
    """По каждому грейду задачи: взят ли его порог — баллов из 100 хватает и все обязательные критерии «да»."""
    return {
        t.grade: score_100 >= t.min_score and all(counted[cid] == "yes" for cid in t.required)
        for t in rubric.thresholds
    }


def highest(reached: dict[str, bool]) -> str | None:
    passed = [g for g, ok in reached.items() if ok]
    return max(passed, key=GRADE_ORDER.get) if passed else None


def grade_of(rubric: Rubric, counted: dict[str, str], score_100: int) -> str | None:
    return highest(reached_grades(rubric, counted, score_100))


def grade_rank(grade: str | None) -> int:
    return GRADE_ORDER.get(grade or "", 0)


def aggregate(rubric: Rubric, runs: list[dict[str, Any]], level: str) -> dict[str, Any]:
    """level — уровень, на который кандидат проходил тест; пройден, если взят порог этого грейда."""
    criteria = []
    counted: dict[str, str] = {}
    for c in rubric.criteria:
        per_run = [r["verdicts"][c.id] for r in runs]
        # медиана; при чётном числе прогонов — нижняя, то есть в пользу строгости
        ranks = sorted(VERDICT_RANK[v["counted"]] for v in per_run)
        final = next(k for k, r in VERDICT_RANK.items() if r == ranks[(len(ranks) - 1) // 2])
        counted[c.id] = final
        source = next(v for v in per_run if v["counted"] == final)
        earned = c.points if final == "yes" else (c.partial_points or 0) if final == "partial" else 0
        criteria.append(
            {
                "id": c.id,
                "text": c.text,
                "kind": c.kind,
                "check": c.check,
                "points": c.points,
                "partial_points": c.partial_points,
                "verdict": final,
                "earned": earned,
                "comment": source["comment"],
                "evidence": source["evidence"] if source["evidence_found"] else "",
                "runs": [v["counted"] for v in per_run],
                # Что сказал судья в каждом прогоне и сколько раз его «да» не подтвердилось цитатой из материалов —
                # чтобы человек на проверке видел, где критерий снят из-за цитаты
                "said": [v["verdict"] for v in per_run],
                "unconfirmed": sum(1 for v in per_run if v["verdict"] != "no" and not v["evidence_found"]),
            }
        )
    score = score_of(rubric, counted)
    score_100 = to_100(score, rubric.max_points)
    reached = reached_grades(rubric, counted, score_100)
    majority_grade = highest(reached)
    run_grades = [r["grade"] for r in runs]
    run_passed = [r["reached"].get(level, False) for r in runs]
    # Прогоны разошлись — засчитываем нижний результат
    unstable = len(set(run_grades)) > 1 or len(set(run_passed)) > 1
    grade = min([majority_grade, *run_grades], key=grade_rank) if unstable else majority_grade
    return {
        "score": score,
        "max_score": rubric.max_points,
        # Балл ИИ по шкале из 100 — то, что видят кандидат и работодатель
        "score_100": score_100,
        "grade": grade,
        "passed": grade is not None,
        # Тест на уровень пройден: взят порог этого грейда по большинству и во всех прогонах
        "level_confirmed": reached.get(level, False) and all(run_passed),
        "unstable": unstable,
        "criteria": criteria,
        "thresholds": [
            {"grade": t.grade, "min_score": t.min_score, "required": t.required, "reached": reached[t.grade]}
            for t in sorted(rubric.thresholds, key=lambda t: GRADE_ORDER[t.grade])
        ],
        "runs": [
            {"run": i + 1, "score": r["score"], "score_100": r["score_100"], "grade": r["grade"]} for i, r in enumerate(runs)
        ],
    }


# --- запуск проверки ---


class Grader:
    def __init__(
        self,
        sessions: async_sessionmaker,
        gateway: Gateway,
        runner: Runner,
        bus: EventBus,
        runs: int = 3,
        on_done: Callable[[str], Awaitable[None]] | None = None,
    ):
        self._sessions = sessions
        self._gateway = gateway
        self._runner = runner
        self._bus = bus
        self._runs = max(1, runs)
        # Вызывается, когда оценка ИИ готова: дальше подтверждение экспертом и смена грейда
        self._on_done = on_done
        self._inflight: set[str] = set()
        self._background: set[asyncio.Task] = set()

    def schedule(self, attempt_id: str) -> None:
        """Запустить проверку в фоне; повторный вызов для той же попытки, пока она проверяется, ничего не делает."""
        if attempt_id in self._inflight:
            return
        self._inflight.add(attempt_id)
        task = asyncio.create_task(self._grade_safely(attempt_id))
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    async def wait_idle(self) -> None:
        while self._background:
            await asyncio.gather(*list(self._background), return_exceptions=True)

    async def stop(self) -> None:
        """При остановке сервиса не ждём долгие вызовы судьи: незаконченная проверка начнётся заново после старта."""
        for task in list(self._background):
            task.cancel()
        await asyncio.gather(*list(self._background), return_exceptions=True)

    async def recover(self) -> None:
        """После перезапуска сервиса проверки, прерванные на середине, начинаются заново."""
        async with self._sessions() as s:
            await s.execute(update(Grading).where(Grading.status == "running").values(status="pending"))
            await s.commit()

    async def ungraded(self) -> list[str]:
        """Завершённые попытки, которые ещё не проверялись или ждут повторной проверки."""
        async with self._sessions() as s:
            rows = await s.execute(
                select(Attempt.id)
                .outerjoin(Grading, Grading.attempt_id == Attempt.id)
                .where(Attempt.status.in_(("submitted", "expired")))
                .where(or_(Grading.attempt_id.is_(None), Grading.status == "pending"))
            )
            return [r[0] for r in rows]

    async def request(self, attempt_id: str) -> None:
        """Перепроверка вручную — например, после правки рубрики или промпта судьи."""
        async with self._sessions() as s:
            attempt = await s.get(Attempt, attempt_id)
            if attempt is None:
                raise NotFound(f"Попытка {attempt_id} не найдена")
            if attempt.status == "active":
                raise Conflict("Попытка ещё не завершена")
            grading = await s.get(Grading, attempt_id)
            if grading is not None and attempt_id not in self._inflight:
                # чтобы до старта новой проверки не показывать старый результат как актуальный
                grading.status = "pending"
                await s.commit()
        self.schedule(attempt_id)

    async def _grade_safely(self, attempt_id: str) -> None:
        try:
            await self.grade(attempt_id)
        except Exception as exc:
            log.exception("grading failed for attempt %s", attempt_id)
            await self._finish_failed(attempt_id, f"{type(exc).__name__}: {exc}")
        finally:
            self._inflight.discard(attempt_id)

    async def grade(self, attempt_id: str) -> None:
        async with self._sessions() as s:
            attempt = await s.get(Attempt, attempt_id)
            if attempt is None:
                raise NotFound(f"Попытка {attempt_id} не найдена")
            if attempt.status == "active":
                raise Conflict("Попытка ещё не завершена")
            events = list(
                (
                    await s.scalars(
                        select(SessionEvent)
                        .where(SessionEvent.attempt_id == attempt_id, ~SessionEvent.type.startswith("grading."))
                        .order_by(SessionEvent.id)
                    )
                ).all()
            )
            grading = await s.get(Grading, attempt_id)
            if grading is None:
                grading = Grading(attempt_id=attempt_id)
                s.add(grading)
            grading.status = "running"
            grading.error = ""
            grading.started_at = utcnow()
            ev = self._event(s, attempt_id, "grading.started", {"runs": self._runs})
            await s.commit()
        self._publish(ev)

        task = Task.model_validate(attempt.task)
        rubric = task.rubric

        # Исходные тесты задачи на решении кандидата: правки кандидата в тестах на этот прогон не влияют
        tests = await self._runner.run(task.with_original_tests(attempt.files), task.run) if task.run else None
        evidence_text = render_evidence(attempt.files, events, attempt.started_at, tests)
        haystack = normalize(evidence_text)
        auto = auto_verdicts(rubric, tests, events, attempt.started_at)
        judge_criteria = [c for c in rubric.criteria if c.id not in auto]
        criteria_lines = [
            f"{c.id} [{'процесс' if c.kind == 'process' else 'решение'}] {c.text}"
            + (" (можно частично)" if c.partial_points is not None else "")
            for c in judge_criteria
        ]
        messages = [
            Message(role="system", content=JUDGE_SYSTEM),
            Message(role="user", content=judge_user_message(task.title, task.statement, criteria_lines, evidence_text)),
        ]
        meta = {  # только для заглушки
            "criteria": [c.id for c in judge_criteria],
            "tests_passed": tests.passed if tests else None,
            "evidence": next((line for line in evidence_text.splitlines() if len(line.strip()) >= 10 and not line.startswith("<")), ""),
        }
        if judge_criteria:
            outputs = await asyncio.gather(
                *(
                    self._gateway.chat_json(
                        "grader",
                        messages,
                        JudgeOutput,
                        priority=Priority.GRADING,
                        attempt_id=attempt_id,
                        prompt_version=JUDGE_PROMPT_VERSION,
                        meta=meta,
                    )
                    for _ in range(self._runs)
                ),
                return_exceptions=True,
            )
        else:  # всё проверяется автоматически — судья не нужен
            outputs = [JudgeOutput(verdicts=[])]
        good = [o for o in outputs if isinstance(o, JudgeOutput)]
        if not good:
            first_error = next(o for o in outputs if isinstance(o, BaseException))
            raise RuntimeError(f"Ни один прогон судьи не удался: {first_error}")

        runs = [evaluate_run(rubric, o, haystack, auto) for o in good]
        result = aggregate(rubric, runs, attempt.level)
        result["failed_runs"] = len(outputs) - len(good)
        result["tests"] = (
            {"passed": tests.passed, "output": tests.summary(4000)} if tests else None
        )

        async with self._sessions() as s:
            grading = await s.get(Grading, attempt_id)
            await s.execute(CriterionVerdict.__table__.delete().where(CriterionVerdict.attempt_id == attempt_id))
            for i, run in enumerate(runs, start=1):
                for cid, v in run["verdicts"].items():
                    s.add(CriterionVerdict(attempt_id=attempt_id, run=i, criterion_id=cid, **v))
            grading.status = "done"
            grading.score = result["score"]
            grading.max_score = result["max_score"]
            grading.grade = result["grade"]
            grading.unstable = result["unstable"]
            grading.result = result
            grading.finished_at = utcnow()
            ev = self._event(
                s,
                attempt_id,
                "grading.completed",
                {"score_100": result["score_100"], "grade": result["grade"], "passed": result["level_confirmed"]},
            )
            await s.commit()
        self._publish(ev)
        if self._on_done is not None:
            try:
                await self._on_done(attempt_id)
            except Exception:  # оценка ИИ уже сохранена — её сбой здесь не перечёркивает
                log.exception("post-grading step failed for attempt %s", attempt_id)

    async def _finish_failed(self, attempt_id: str, error: str) -> None:
        async with self._sessions() as s:
            grading = await s.get(Grading, attempt_id)
            if grading is None:
                if await s.get(Attempt, attempt_id) is None:
                    return
                grading = Grading(attempt_id=attempt_id)
                s.add(grading)
            grading.status = "failed"
            grading.error = error
            grading.finished_at = utcnow()
            ev = self._event(s, attempt_id, "grading.failed", {"error": error})
            await s.commit()
        self._publish(ev)

    # События проверки пишем в тот же журнал попытки, чтобы фронт узнал о результате по WebSocket.
    def _event(self, s, attempt_id: str, type_: str, payload: dict[str, Any]) -> SessionEvent:
        ev = SessionEvent(attempt_id=attempt_id, type=type_, payload=payload, created_at=utcnow())
        s.add(ev)
        return ev

    def _publish(self, ev: SessionEvent) -> None:
        self._bus.publish(ev.attempt_id, {"type": "event", "event": event_view(ev)})
