"""Итог теста и грейд кандидата — экраны «Грейд и тесты» и «Профиль и категория».

- Итог теста — оценка LLM-судьи после постобработки, балл по шкале 0–100 с округлением вверх.
- Уход со вкладки во время теста запрещён: любой уход помечает попытку, решает человек. Аннулировал —
  грейд, полученный этой попыткой, снимается (возвращается прежний), тесты кандидата заморожены на 30 дней.
- Отчёт ИИ видят люди и могут его исправить: поменять вердикты по критериям. Балл пересчитывается по рубрике,
  итог теста — по исправленным вердиктам; поменялся итог — вслед за ним меняется грейд. Оценка ИИ сохраняется.
- Тест пройден, если взят порог грейда, на который он проходился. Тогда грейд меняется на этот уровень,
  следующая смена — через 3 месяца. Принудительного понижения нет: непройденный тест грейд не трогает.
- После непройденного теста уровень ниже доступен сразу, тот же уровень — через 30 дней.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bus import EventBus
from app.db import utcnow
from app.grading import highest, reached_grades, score_of, to_100
from app.models import Attempt, AttemptReview, GradeRecord, Grading, SessionEvent
from app.service import TAB_EVENTS, BadRequest, Conflict, NotFound, event_view, tab_violations
from app.tasks import GRADE_ORDER, Task

LEVELS = sorted(GRADE_ORDER, key=GRADE_ORDER.get)


@dataclass
class Final:
    score: int
    passed: bool
    at: datetime


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() + "Z" if value else None


def _final(grading: Grading | None) -> Final | None:
    """None — оценка ещё не готова."""
    if grading is None or grading.status != "done":
        return None
    fix = grading.result.get("correction")
    if fix:  # человек исправил вердикты — итог по исправленным
        return Final(fix["score_100"], fix["level_confirmed"], grading.finished_at)
    return Final(_ai_score(grading.result), grading.result["level_confirmed"], grading.finished_at)


def _final_view(final: Final | None) -> dict[str, Any] | None:
    return None if final is None else {"score": final.score, "passed": final.passed, "at": _iso(final.at)}


class GradeService:
    def __init__(
        self,
        sessions: async_sessionmaker,
        bus: EventBus,
        *,
        cooldown_days: int = 90,
        retry_days: int = 30,
        freeze_days: int = 30,
    ):
        self._sessions = sessions
        self._bus = bus
        self._cooldown = timedelta(days=cooldown_days)
        self._retry = timedelta(days=retry_days)
        self._freeze = timedelta(days=freeze_days)

    # --- итог теста ---

    async def result(self, attempt_id: str) -> dict[str, Any]:
        async with self._sessions() as s:
            attempt = await s.get(Attempt, attempt_id)
            if attempt is None:
                raise NotFound(f"Попытка {attempt_id} не найдена")
            grading = await s.get(Grading, attempt_id)
            check = await self._check(s, attempt)
        if grading is None:
            return {"attempt_id": attempt_id, "status": "not_submitted" if attempt.status == "active" else "pending", **check}
        out: dict[str, Any] = {
            "attempt_id": attempt_id,
            "status": grading.status,
            "error": grading.error or None,
            "finished_at": _iso(grading.finished_at),
        }
        if grading.status == "done":
            out |= _with_correction(grading.result)
            out["ai_score"] = _ai_score(grading.result)  # оценка ИИ — без правки человека
        out["final"] = _final_view(_final(grading))
        return out | check

    async def _check(self, s, attempt: Attempt) -> dict[str, Any]:
        """Нарушения в попытке и решение человека по ним."""
        events = (
            await s.scalars(
                select(SessionEvent)
                .where(SessionEvent.attempt_id == attempt.id, SessionEvent.type.in_(TAB_EVENTS))
                .order_by(SessionEvent.id)
            )
        ).all()
        violations = tab_violations(list(events), attempt.submitted_at or utcnow())
        review = await s.get(AttemptReview, attempt.id)
        return {
            "violations": violations,
            "review": _review_view(review),
            # Есть нарушения, а человек ещё не решил
            "needs_review": violations["count"] > 0 and review is None,
        }

    # --- решение человека по попытке ---

    async def review(
        self, attempt_id: str, reviewer: str, annul: bool, comment: str, verdicts: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Человек решил по попытке: подтвердил оценку ИИ, исправил вердикты по критериям или аннулировал.
        Аннулировал — грейд, полученный этой попыткой, снимается, тесты кандидата заморожены.
        Исправил — итог по исправленным вердиктам; поменялся итог — меняется и грейд. Решение принимается один раз."""
        async with self._sessions() as s:
            attempt = await s.get(Attempt, attempt_id)
            if attempt is None:
                raise NotFound(f"Попытка {attempt_id} не найдена")
            if attempt.status == "active":
                raise Conflict("Тест ещё идёт")
            if await s.get(AttemptReview, attempt_id) is not None:
                raise Conflict("Решение по попытке уже принято")
            grading = await s.get(Grading, attempt_id)
            before = after = None
            if verdicts and not annul:
                if grading is None or grading.status != "done":
                    raise Conflict("Оценка ИИ ещё не готова")
                fix = _correction(attempt, grading.result, verdicts, reviewer)
                if fix is not None:
                    before = _final(grading)
                    grading.result = {**grading.result, "correction": fix}
                    after = _final(grading)
            s.add(AttemptReview(attempt_id=attempt_id, reviewer=reviewer, annulled=annul, comment=comment, decided_at=utcnow()))
            payload = {"reviewer": reviewer, "annulled": annul, "comment": comment}
            if after is not None:
                payload["verdicts"] = grading.result["correction"]["verdicts"]
            events = [_event(s, attempt_id, "review.decided", payload)]
            changed = None
            if annul:
                await s.flush()  # поиск прежнего грейда должен уже видеть эту попытку аннулированной
                changed = await self._restore_grade(s, attempt)
            elif after is not None and after.passed != before.passed:
                if after.passed:
                    if await self._latest_in_category(s, attempt):
                        changed = await self._set_grade(s, attempt, after)
                else:
                    await s.flush()  # прежний грейд ищем уже по исправленному итогу
                    changed = await self._restore_grade(s, attempt)
            if changed:
                events.append(_event(s, attempt_id, "grade.changed", changed))
            await s.commit()
        for ev in events:
            self._publish(ev)
        return await self.result(attempt_id)

    async def _latest_in_category(self, s, attempt: Attempt) -> bool:
        """Правка делает тест пройденным — грейд меняем, только если позже кандидат не получил грейд другим тестом."""
        record = await s.get(GradeRecord, (attempt.candidate_id, _key(attempt.category)))
        if record is None or record.attempt_id == attempt.id:
            return True
        holder = await s.get(Attempt, record.attempt_id)
        return holder is None or holder.started_at <= attempt.started_at

    async def queue(self) -> list[dict[str, Any]]:
        """«Проверка оценок»: сданные попытки с готовой оценкой ИИ. Сначала помеченные за уход со вкладки
        и ещё не решённые, потом ждущие решения, потом решённые; внутри — новые сверху."""
        async with self._sessions() as s:
            attempts = (await s.scalars(select(Attempt).where(Attempt.status != "active").order_by(Attempt.submitted_at.desc()))).all()
            ids = [a.id for a in attempts]
            gradings = {g.attempt_id: g for g in (await s.scalars(select(Grading).where(Grading.attempt_id.in_(ids)))).all()}
            reviews = {r.attempt_id: r for r in (await s.scalars(select(AttemptReview).where(AttemptReview.attempt_id.in_(ids)))).all()}
            tab: dict[str, list[SessionEvent]] = defaultdict(list)
            for ev in (
                await s.scalars(
                    select(SessionEvent)
                    .where(SessionEvent.attempt_id.in_(ids), SessionEvent.type.in_(TAB_EVENTS))
                    .order_by(SessionEvent.id)
                )
            ).all():
                tab[ev.attempt_id].append(ev)
        items = []
        for a in attempts:
            g = gradings.get(a.id)
            if g is None or g.status != "done":
                continue  # человеку показываем то, что ИИ уже оценил
            violations = tab_violations(tab[a.id], a.submitted_at or utcnow())
            review = reviews.get(a.id)
            items.append(
                {
                    "attempt_id": a.id,
                    "candidate_id": a.candidate_id,
                    "category": a.category,
                    "level": a.level,
                    "task_id": a.task["id"],
                    "task_title": a.task["title"],
                    "submitted_at": _iso(a.submitted_at),
                    "ai_score": _ai_score(g.result),
                    "final": _final_view(_final(g)),
                    "violations": violations,
                    "needs_review": violations["count"] > 0 and review is None,
                    "review": _review_view(review),
                }
            )
        items.sort(key=lambda x: (not x["needs_review"], x["review"] is not None))  # сортировка устойчивая: новые сверху
        return items

    async def _restore_grade(self, s, attempt: Attempt) -> dict[str, Any] | None:
        """Грейд в категории держится на аннулированной попытке — возвращаем прежний: последний тест,
        пройденный без аннулирования. Такого нет — грейда в категории больше нет."""
        record = await s.get(GradeRecord, (attempt.candidate_id, _key(attempt.category)))
        if record is None or record.attempt_id != attempt.id:
            return None
        annulled = set((await s.scalars(select(AttemptReview.attempt_id).where(AttemptReview.annulled.is_(True)))).all())
        best = None
        for a in (await s.scalars(select(Attempt).where(Attempt.candidate_id == attempt.candidate_id))).all():
            if a.id in annulled or _key(a.category) != _key(attempt.category):
                continue
            final = _final(await s.get(Grading, a.id))
            if final is not None and final.passed and (best is None or final.at > best[1].at):
                best = (a, final)
        previous = record.grade
        if best is None:
            await s.delete(record)
            return {"category": attempt.category, "from": previous, "to": None}
        a, final = best
        record.grade, record.score, record.attempt_id = a.level, final.score, a.id
        record.confirmed_at, record.next_change_at = final.at, final.at + self._cooldown
        return {"category": attempt.category, "from": previous, "to": a.level}

    async def on_ai_done(self, attempt_id: str) -> None:
        """Оценка готова — она и есть итог: при успехе грейд кандидата меняется на уровень теста."""
        async with self._sessions() as s:
            attempt = await s.get(Attempt, attempt_id)
            final = _final(await s.get(Grading, attempt_id))
            if attempt is None or final is None:
                return
            events = [_event(s, attempt_id, "result.final", {"score": final.score, "passed": final.passed})]
            if final.passed:
                events.append(_event(s, attempt_id, "grade.changed", await self._set_grade(s, attempt, final)))
            await s.commit()
        for ev in events:
            self._publish(ev)

    async def _set_grade(self, s, attempt: Attempt, final: Final) -> dict[str, Any]:
        """Тест пройден — грейд в категории становится уровнем теста, следующая смена — через 3 месяца."""
        record = await s.get(GradeRecord, (attempt.candidate_id, _key(attempt.category)))
        previous = record.grade if record else None
        if record is None:
            record = GradeRecord(candidate_id=attempt.candidate_id, category=_key(attempt.category))
            s.add(record)
        now = utcnow()
        record.grade = attempt.level
        record.score = final.score
        record.attempt_id = attempt.id
        record.confirmed_at = now
        record.next_change_at = now + self._cooldown
        return {"category": attempt.category, "from": previous, "to": attempt.level}

    # --- грейд, доступные тесты, история ---

    async def status(self, candidate_id: str, category: str) -> dict[str, Any]:
        """Данные для экрана «Грейд и тесты»: текущий грейд, когда можно менять, какие тесты доступны."""
        now = utcnow()
        async with self._sessions() as s:
            record = await s.get(GradeRecord, (candidate_id, _key(category)))
            attempts = (await s.scalars(select(Attempt).where(Attempt.candidate_id == candidate_id))).all()
            finals = await self._finals(s, [a.id for a in attempts])
            reviews = (
                await s.scalars(select(AttemptReview).where(AttemptReview.attempt_id.in_([a.id for a in attempts])))
            ).all()
        frozen_until = max((r.decided_at + self._freeze for r in reviews if r.annulled), default=None)
        if frozen_until is not None and now >= frozen_until:
            frozen_until = None
        tests = []
        for level in LEVELS:
            reason, available_from = self._why_unavailable(level, category, record, attempts, finals, now, frozen_until)
            tests.append({"level": level, "available": reason is None, "reason": reason, "available_from": _iso(available_from)})
        return {
            "candidate_id": candidate_id,
            "category": category,
            "grade": record.grade if record else None,
            "score": record.score if record else None,
            "confirmed_at": _iso(record.confirmed_at) if record else None,
            # «Смена грейда: доступно с …»; null — грейда ещё нет, тест можно проходить сразу
            "next_change_at": _iso(record.next_change_at) if record else None,
            "change_available": record is None or now >= record.next_change_at,
            # Попытку аннулировали — до этой даты тесты недоступны; null — заморозки нет
            "frozen_until": _iso(frozen_until),
            "tests": tests,
        }

    async def check_can_start(self, candidate_id: str, category: str, level: str) -> None:
        status = await self.status(candidate_id, category)
        entry = next(t for t in status["tests"] if t["level"] == level)
        if not entry["available"]:
            when = f" (доступно с {_ru_date(entry['available_from'])})" if entry["available_from"] else ""
            raise Conflict(entry["reason"] + when)

    async def history(self, candidate_id: str) -> list[dict[str, Any]]:
        """«История тестов»: тест, балл, итог. Новые сверху."""
        async with self._sessions() as s:
            attempts = (
                await s.scalars(select(Attempt).where(Attempt.candidate_id == candidate_id).order_by(Attempt.started_at.desc()))
            ).all()
            ids = [a.id for a in attempts]
            gradings = {g.attempt_id: g for g in (await s.scalars(select(Grading).where(Grading.attempt_id.in_(ids)))).all()}
            reviews = {r.attempt_id: r for r in (await s.scalars(select(AttemptReview).where(AttemptReview.attempt_id.in_(ids)))).all()}
            leaves: dict[str, int] = defaultdict(int)
            for aid in (
                await s.scalars(select(SessionEvent.attempt_id).where(SessionEvent.attempt_id.in_(ids), SessionEvent.type == "tab.left"))
            ).all():
                leaves[aid] += 1
        items = []
        for a in attempts:
            g = gradings.get(a.id)
            items.append(
                {
                    "attempt_id": a.id,
                    "task_id": a.task["id"],
                    "task_title": a.task["title"],
                    "category": a.category,
                    "level": a.level,
                    "started_at": _iso(a.started_at),
                    "submitted_at": _iso(a.submitted_at),
                    "status": a.status,
                    "grading_status": g.status if g else ("not_submitted" if a.status == "active" else "pending"),
                    "ai_score": _ai_score(g.result) if g and g.status == "done" else None,
                    "final": _final_view(_final(g)),
                    "tab_leaves": leaves[a.id],
                    "annulled": a.id in reviews and reviews[a.id].annulled,
                }
            )
        return items

    async def _finals(self, s, attempt_ids: list[str]) -> dict[str, Final | str]:
        """Итог по каждой попытке; вместо итога — "checking", пока он не готов, или "broken", если проверка упала."""
        gradings = {g.attempt_id: g for g in (await s.scalars(select(Grading).where(Grading.attempt_id.in_(attempt_ids)))).all()}
        out: dict[str, Final | str] = {}
        for aid in attempt_ids:
            g = gradings.get(aid)
            final = _final(g)
            out[aid] = final if final is not None else ("broken" if g is not None and g.status == "failed" else "checking")
        return out

    def _why_unavailable(self, level, category, record, attempts, finals, now, frozen_until) -> tuple[str | None, datetime | None]:
        if any(a.status == "active" for a in attempts):
            return "Сначала завершите текущий тест", None
        if frozen_until is not None:
            return "Тесты заморожены: попытка аннулирована", frozen_until
        if record is not None and record.grade == level:
            return "Это ваш текущий грейд", None
        if record is not None and now < record.next_change_at:
            return "Грейд можно менять раз в 3 месяца", record.next_change_at
        same_level = [
            a
            for a in attempts
            if a.category.lower() == category.lower() and a.level == level and finals[a.id] != "broken"
        ]
        if any(finals[a.id] == "checking" for a in same_level):
            return "Предыдущий тест на этот уровень ещё проверяется", None
        failed = [a for a in same_level if not finals[a.id].passed]
        if failed:
            retry_at = max(a.submitted_at for a in failed) + self._retry
            if now < retry_at:
                return "Тест на этот уровень можно повторить через 30 дней после непройденного", retry_at
        return None, None

    def _publish(self, ev: SessionEvent) -> None:
        self._bus.publish(ev.attempt_id, {"type": "event", "event": event_view(ev)})


def _key(category: str) -> str:
    """Грейд хранится по категории без учёта регистра: «Backend» и «backend» — одно и то же."""
    return category.strip().lower()


def _correction(attempt: Attempt, result: dict[str, Any], verdicts: dict[str, str], reviewer: str) -> dict[str, Any] | None:
    """Правка человека: новые вердикты → баллы и пороги по рубрике задачи. None — правка ничего не меняет."""
    rubric = Task.model_validate(attempt.task).rubric
    by_id = {c.id: c for c in rubric.criteria}
    ai = {c["id"]: c["verdict"] for c in result["criteria"]}
    for cid, verdict in verdicts.items():
        c = by_id.get(cid)
        if c is None:
            raise BadRequest(f"В задаче нет критерия {cid}")
        if c.check == "tests":
            raise BadRequest(f"Критерий {cid} засчитывается по автотестам, его не исправляют")
        if verdict == "partial" and c.partial_points is None:
            raise BadRequest(f"У критерия {cid} нет оценки «частично»")
    changed = {cid: v for cid, v in verdicts.items() if v != ai.get(cid)}
    if not changed:
        return None
    counted = {cid: changed.get(cid, v) for cid, v in ai.items()}
    score = score_of(rubric, counted)
    score_100 = to_100(score, rubric.max_points)
    reached = reached_grades(rubric, counted, score_100)
    return {
        "reviewer": reviewer,
        "at": _iso(utcnow()),
        "verdicts": changed,
        "score": score,
        "score_100": score_100,
        "grade": highest(reached),
        "level_confirmed": reached.get(attempt.level, False),
        "thresholds": [
            {"grade": t.grade, "min_score": t.min_score, "required": t.required, "reached": reached[t.grade]}
            for t in sorted(rubric.thresholds, key=lambda t: GRADE_ORDER[t.grade])
        ],
    }


def _with_correction(result: dict[str, Any]) -> dict[str, Any]:
    """Отчёт с правкой человека поверх оценки ИИ: вердикты, баллы, пороги. Вердикт ИИ остаётся в ai_verdict."""
    fix = result.get("correction")
    if not fix:
        return result
    criteria = []
    for c in result["criteria"]:
        v = fix["verdicts"].get(c["id"])
        if v is None:
            criteria.append(c)
            continue
        earned = c["points"] if v == "yes" else (c["partial_points"] or 0) if v == "partial" else 0
        criteria.append({**c, "ai_verdict": c["verdict"], "verdict": v, "earned": earned, "corrected": True})
    return {
        **result,
        "criteria": criteria,
        "score": fix["score"],
        "grade": fix["grade"],
        "passed": fix["grade"] is not None,
        "level_confirmed": fix["level_confirmed"],
        "thresholds": fix["thresholds"],
        "correction": {"reviewer": fix["reviewer"], "at": fix["at"], "score": fix["score_100"], "changed": sorted(fix["verdicts"])},
    }


def _ru_date(iso: str) -> str:
    """2027-01-08T… → 08.01.2027"""
    year, month, day = iso[:10].split("-")
    return f"{day}.{month}.{year}"


def _review_view(review: AttemptReview | None) -> dict[str, Any] | None:
    if review is None:
        return None
    return {"reviewer": review.reviewer, "annulled": review.annulled, "comment": review.comment, "at": _iso(review.decided_at)}


def _event(s, attempt_id: str, type_: str, payload: dict[str, Any]) -> SessionEvent:
    ev = SessionEvent(attempt_id=attempt_id, type=type_, payload=payload, created_at=utcnow())
    s.add(ev)
    return ev


def _ai_score(result: dict[str, Any]) -> int:
    """Балл из 100. В проверках, сделанных до появления шкалы из 100, считаем его из сырых баллов."""
    if "score_100" in result:
        return result["score_100"]
    return to_100(result["score"], result["max_score"]) if result.get("max_score") else 0
