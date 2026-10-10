"""Генерация задач в банк: LLM пишет задачу под категории и грейды, платформа проверяет её автоматически.

1. Модель присылает черновик по строгой схеме: условие, стартовые файлы и тесты, эталон,
   критерии приёмки и пороги прохождения по грейдам.
2. Проверки:
   - пороги стоят ровно на запрошенные грейды, критерии и пороги согласованы;
   - у задач bug и feature есть тесты и эталон; эталон не меняет тесты;
   - тесты на стартовом коде падают (иначе кандидату нечего делать), но не из-за того, что код не запускается;
   - тесты на эталоне проходят (иначе задача нерешаема).
3. Не прошло — модели показывают, что не так, и она присылает исправленный черновик.
4. Прошло — задача сразу попадает в банк.
"""

import asyncio
import io
import json
import logging
import random
import re
import secrets
import tokenize
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import utcnow
from app.llm.gateway import Gateway, extract_json
from app.llm.types import Message, Priority
from app.models import TaskGeneration, TaskRow
from app.prompts import TASKGEN_PROMPT_VERSION, TASKGEN_SYSTEM, taskgen_user_message
from app.sandbox import RunResult, Runner
from app.service import BadRequest, NotFound, normalize_path
from app.tasks import (
    GRADE_ORDER,
    TEST_RUNNER,
    TEST_RUNNER_PATH,
    Criterion,
    Grade,
    GradeThreshold,
    Rubric,
    RunSpec,
    Task,
    TaskType,
    is_test_file,
    normalize_category,
)

log = logging.getLogger(__name__)

# Тест на грейд — одна задача на 30 минут, если время не задано явно
DEFAULT_TIME_LIMIT = {"intern": 30, "junior": 30, "middle": 30, "senior": 30}
# Системный дизайн — с Middle
TYPES_FOR_GRADE: dict[str, list[str]] = {
    "intern": ["bug", "feature"],
    "junior": ["bug", "feature"],
    "middle": ["bug", "feature", "design"],
    "senior": ["bug", "feature", "design"],
}
_BROKEN_START = ("SyntaxError", "IndentationError", "ModuleNotFoundError", "ImportError: cannot import")
# Живой GigaChat писал в стартовом коде «# BUG: должны быть только положительные» — задача теряет смысл
_HINT = re.compile(r"(?i)#.*(\bbug\b|\bfixme\b|ошибк|ошибочн|\bбаг|исправ)|\b(BUG|FIXME)\b")


class GenerationRequest(BaseModel):
    """То, что задаёт фронт: категории, грейды и, по желанию, тип, тему и лимит времени."""

    categories: list[str] = Field(min_length=1, description="Направления как на сайте, например [\"Backend\"] или [\"data\"]")
    grades: list[Grade] = Field(min_length=1, description="Один грейд — один порог приёма; несколько — порог на каждый")
    type: TaskType | None = Field(default=None, description="bug | feature | design; не задан — выбирается случайно")
    brief: str = Field(default="", max_length=5000, description="Описание вакансии или тема: домен, стек, команда")
    time_limit_min: int | None = Field(default=None, ge=5, le=180)

    @field_validator("categories")
    @classmethod
    def _clean(cls, value: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(normalize_category(c) for c in value if c.strip()))
        if not cleaned:
            raise ValueError("нужна хотя бы одна категория")
        return cleaned

    @model_validator(mode="after")
    def _consistent(self) -> "GenerationRequest":
        if len(set(self.grades)) != len(self.grades):
            raise ValueError("грейды не должны повторяться")
        self.grades = sorted(self.grades, key=GRADE_ORDER.get)
        if self.type == "design" and {"intern", "junior"} & set(self.grades):
            raise ValueError("задачи на системный дизайн — с Middle")
        return self


class DraftFile(BaseModel):
    path: str
    content: str


class TaskMeta(BaseModel):
    """Всё, кроме файлов: идёт в ответе модели JSON-ом в блоке === META ===."""

    title: str = Field(min_length=5, max_length=120)
    statement: str = Field(min_length=40, description="Условие: ситуация, симптом или постановка, ограничения")
    assessed: list[str] = Field(min_length=2, max_length=5, description="«Что оценивается» для кандидата")
    criteria: list[Criterion] = Field(min_length=4, max_length=15)
    thresholds: list[GradeThreshold] = Field(min_length=1, description="Ровно по одному на каждый запрошенный грейд")


class TaskDraft(TaskMeta):
    files: list[DraftFile] = Field(min_length=1, description="Стартовые файлы кандидата, включая тесты test_*.py")
    reference_files: list[DraftFile] = Field(default_factory=list, description="Эталон: изменённые или новые файлы целиком")


# Код задачи не кладём в JSON: живой GigaChat ломал экранирование и скобки в ответе на 5+ тыс. символов.
# Файлы идут блоками как есть, JSON — только метаданные.
DRAFT_FORMAT = """Формат ответа — строго такой, без пояснений до и после:

=== META ===
{meta_example}
=== FILE files/<путь стартового файла> ===
<содержимое файла как есть, без markdown>
=== FILE reference/<путь файла эталона> ===
<содержимое файла как есть>

Блок === FILE … === — на каждый файл. META — JSON по схеме:
{schema}"""

# Префикс files/ модель иногда забывает («=== FILE test_x.py ===») — такой файл считаем стартовым
_BLOCK = re.compile(r"^===\s*(META|FILE\s+(?:(files|reference)/)?(.+?))\s*===[ \t]*$", re.MULTILINE)
_FENCE = re.compile(r"^```[\w+-]*\n(.*?)\n?```$", re.DOTALL)


def draft_format_instruction() -> str:
    example = '{"title": "...", "statement": "...", "assessed": ["..."], "criteria": [...], "thresholds": [...]}'
    return DRAFT_FORMAT.format(meta_example=example, schema=json.dumps(TaskMeta.model_json_schema(), ensure_ascii=False))


def parse_draft(text: str) -> TaskDraft:
    """Ответ модели → черновик. ValueError с понятным текстом, если формат нарушен — его покажут модели."""
    blocks = list(_BLOCK.finditer(text))
    if not blocks:
        raise ValueError("нет блоков === META === и === FILE files/… ===")
    meta_text = None
    files: list[DraftFile] = []
    reference: list[DraftFile] = []
    for i, block in enumerate(blocks):
        end = blocks[i + 1].start() if i + 1 < len(blocks) else len(text)
        body = text[block.end() : end].strip("\n")
        fenced = _FENCE.match(body.strip())
        if fenced:  # модель всё же обернула код в ```
            body = fenced.group(1)
        if block.group(1) == "META":
            meta_text = body
        else:
            target = reference if block.group(2) == "reference" else files
            target.append(DraftFile(path=block.group(3).strip(), content=body.rstrip() + "\n"))
    if meta_text is None:
        raise ValueError("нет блока === META ===")
    try:
        meta = TaskMeta.model_validate_json(extract_json(meta_text))
        return TaskDraft(**meta.model_dump(), files=files, reference_files=reference)
    except ValidationError as exc:
        details = "; ".join(f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in exc.errors()[:8])
        raise ValueError(f"META или файлы не по схеме: {details}") from exc


def _collect_files(files: list[DraftFile], field: str, problems: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for f in files:
        try:
            path = normalize_path(f.path)
        except BadRequest as exc:
            problems.append(f"{field}: {exc}")
            continue
        if path in out:
            problems.append(f"{field}: файл {path} указан дважды")
        out[path] = f.content
    return out


def build_task(
    draft: TaskDraft, req: GenerationRequest, task_type: str, time_limit: int, task_id: str
) -> tuple[Task | None, list[str], list[str]]:
    """Черновик → задача. Возвращает задачу (если её вообще можно собрать), проблемы — их исправляет модель,
    и то, что платформа поправила сама: в мелочах GigaChat слушается плохо, тратить на них попытки дорого."""
    problems: list[str] = []
    fixes: list[str] = []
    files = _collect_files(draft.files, "files", problems)
    reference = _collect_files(draft.reference_files, "reference_files", problems)
    has_tests = any(is_test_file(p) for p in files)
    if task_type in ("bug", "feature"):
        if not has_tests:
            problems.append(f"Для задачи типа {task_type} нужны тесты unittest в файлах test_*.py")
        if not reference:
            problems.append("Нужно эталонное решение в reference_files")
    touched = sorted(p for p in reference if is_test_file(p) and p in files)
    if touched:
        problems.append(f"Эталон не должен менять тесты: {', '.join(touched)}")
    if task_type == "bug":
        for path in [p for p in files if not is_test_file(p) and p.endswith(".py")]:
            files[path], removed = _strip_hint_comments(files[path])
            fixes += [f"{path}: убран комментарий-подсказка «{c}»" for c in removed]
        hints = [
            f"{path}: {line.strip()}"
            for path, content in files.items()
            if not is_test_file(path)
            for line in content.splitlines()
            if _HINT.search(line)
        ]
        if hints:
            problems.append(
                "В стартовом коде подсказки, где ошибка, — найти её должен кандидат. Убери их из докстрингов и строк:\n"
                + "\n".join(hints[:5])
            )
    criteria = [c.model_copy() for c in draft.criteria]
    auto = [c for c in criteria if c.check == "tests"]
    for extra in auto[1:]:
        extra.check = "judge"
        fixes.append(f"критерий {extra.id}: check=tests → judge (автоматический критерий должен быть один)")
    if has_tests:
        files[TEST_RUNNER_PATH] = TEST_RUNNER  # файл запуска всегда наш
        # unittest ищет тесты только в папках-пакетах, а GigaChat кладёт их в tests/ без __init__.py:
        # тогда не находится ни одного теста, и модель зря переписывает годный черновик
        for folder in sorted({p.rsplit("/", 1)[0] for p in files if is_test_file(p) and "/" in p}):
            parts = folder.split("/")
            for depth in range(1, len(parts) + 1):
                init = "/".join(parts[:depth]) + "/__init__.py"
                if init not in files:
                    files[init] = ""
                    fixes.append(f"{init}: добавлен пустой файл, иначе unittest не найдёт тесты в папке")
    try:
        task = Task(
            id=task_id,
            title=draft.title,
            type=task_type,
            categories=req.categories,
            grades=req.grades,
            time_limit_min=time_limit,
            statement=draft.statement,
            assessed=draft.assessed,
            files=files,
            reference_files=reference,
            run=RunSpec() if has_tests else None,
            rubric=Rubric(criteria=criteria, thresholds=draft.thresholds),
        )
    except ValidationError as exc:
        problems += [f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}".lstrip(": ") for e in exc.errors()]
        return None, problems, fixes
    return task, problems, fixes


def _strip_hint_comments(source: str) -> tuple[str, list[str]]:
    """Вырезает комментарии, выдающие ошибку. Комментарии ищет tokenize — строки и код не задеваются."""
    try:
        comments = [
            tok
            for tok in tokenize.generate_tokens(io.StringIO(source).readline)
            if tok.type == tokenize.COMMENT and _HINT.search(tok.string)
        ]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source, []
    if not comments:
        return source, []
    lines = source.splitlines(keepends=True)
    drop: set[int] = set()
    for tok in comments:
        row, col = tok.start[0] - 1, tok.start[1]
        line = lines[row]
        code = line[:col].rstrip()
        if code:
            lines[row] = code + ("\n" if line.endswith("\n") else "")
        else:
            drop.add(row)  # строка была только комментарием
    cleaned = "".join(line for i, line in enumerate(lines) if i not in drop)
    return cleaned, [tok.string.lstrip("# ").strip() for tok in comments]


_KEY_ERROR = re.compile(r"^(?:\w+(?:Error|Exception)\b.*|FAIL: .*|ERROR: .*)$")


def _explain(result: RunResult) -> str:
    """Сначала — короткая выжимка ошибок: в полном выводе модель тонет в traceback."""
    output = f"{result.stdout}\n{result.stderr}"
    key = list(dict.fromkeys(line.strip() for line in output.splitlines() if _KEY_ERROR.match(line.strip())))[:8]
    head = "Ключевые ошибки:\n" + "\n".join(f"  {line}" for line in key) + "\n" if key else ""
    return head + "Вывод тестов:\n" + result.summary(1500)


async def check_tests(task: Task, runner: Runner) -> tuple[list[str], dict[str, Any]]:
    if task.run is None:
        return [], {}
    start = await runner.run(task.files, task.run)
    reference = await runner.run({**task.files, **task.reference_files}, task.run)
    problems = []
    start_output = f"{start.stdout}\n{start.stderr}"
    if any(marker in start_output for marker in _BROKEN_START):
        problems.append("Стартовый код не запускается — тесты должны падать из-за ошибки в логике, а не в синтаксисе или импортах.\n" + _explain(start))
    elif task.type in ("bug", "feature") and start.passed:
        problems.append(
            "Тесты проходят на стартовом коде — кандидату нечего исправлять. Добавь тест, который воспроизводит симптом "
            "из условия: он проверяет ровно то поведение, которым стартовый код отличается от эталона, и падает на стартовом коде. "
            "Если симптом не воспроизвести в одном процессе, упрости ситуацию или смоделируй окружение классом.\n"
            "Вывод тестов на стартовом коде:\n" + start.summary(1200)
        )
    if not reference.passed:
        problems.append("Тесты не проходят на эталонном решении.\n" + _explain(reference))
    report = {
        "start": {"passed": start.passed, "output": start.summary(1500)},
        "reference": {"passed": reference.passed, "output": reference.summary(1500)},
    }
    return problems, report


class TaskGenerator:
    def __init__(
        self,
        sessions: async_sessionmaker,
        gateway: Gateway,
        runner: Runner,
        *,
        fix_attempts: int = 3,
        packages: list[str] | None = None,
        max_tokens: int = 8000,
    ):
        self._sessions = sessions
        self._gateway = gateway
        self._runner = runner
        self._fix_attempts = max(0, fix_attempts)
        self._packages = packages or []
        self._max_tokens = max_tokens
        self._background: set[asyncio.Task] = set()

    async def create(self, req: GenerationRequest) -> dict[str, Any]:
        async with self._sessions() as s:
            job = TaskGeneration(request=req.model_dump(), status="pending", report=[])
            s.add(job)
            await s.commit()
        self.schedule(job.id)
        return _job_view(job)

    def schedule(self, job_id: str) -> None:
        task = asyncio.create_task(self._run_safely(job_id))
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    async def recover(self) -> None:
        """После перезапуска сервиса незаконченные генерации запускаются заново."""
        async with self._sessions() as s:
            await s.execute(update(TaskGeneration).where(TaskGeneration.status == "running").values(status="pending"))
            pending = (await s.scalars(select(TaskGeneration.id).where(TaskGeneration.status == "pending"))).all()
            await s.commit()
        for job_id in pending:
            self.schedule(job_id)

    async def wait_idle(self) -> None:
        while self._background:
            await asyncio.gather(*list(self._background), return_exceptions=True)

    async def stop(self) -> None:
        for task in list(self._background):
            task.cancel()
        await asyncio.gather(*list(self._background), return_exceptions=True)

    async def job(self, job_id: str) -> dict[str, Any]:
        async with self._sessions() as s:
            job = await s.get(TaskGeneration, job_id)
        if job is None:
            raise NotFound(f"Генерация {job_id} не найдена")
        return _job_view(job)

    async def _run_safely(self, job_id: str) -> None:
        try:
            await self.run(job_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("task generation %s failed", job_id)
            await self._update(job_id, status="failed", error=f"{type(exc).__name__}: {exc}", finished_at=utcnow())

    async def run(self, job_id: str) -> None:
        async with self._sessions() as s:
            job = await s.get(TaskGeneration, job_id)
            if job is None or job.status not in ("pending", "running"):
                return
            job.status = "running"
            job.report = []
            await s.commit()
            req = GenerationRequest.model_validate(job.request)

        task_type = req.type or random.choice(TYPES_FOR_GRADE[req.grades[0]])
        time_limit = req.time_limit_min or DEFAULT_TIME_LIMIT[req.grades[-1]]
        packages = (
            "только стандартная библиотека и пакеты " + ", ".join(self._packages)
            if self._packages
            else "только стандартная библиотека, без сторонних пакетов"
        )
        messages = [
            Message(
                role="system",
                content=TASKGEN_SYSTEM.format(time_limit=time_limit, packages=packages) + "\n\n" + draft_format_instruction(),
            ),
            Message(role="user", content=taskgen_user_message(req.categories, req.grades, task_type, time_limit, req.brief)),
        ]
        report: list[dict[str, Any]] = []
        for attempt in range(self._fix_attempts + 1):
            result = await self._gateway.chat(
                "task_gen",
                messages,
                priority=Priority.BACKGROUND,
                prompt_version=TASKGEN_PROMPT_VERSION,
                max_tokens=self._max_tokens,
                meta={"categories": req.categories, "grades": req.grades, "type": task_type, "attempt": attempt},
            )
            raw = result.message.content
            task, tests, problems, fixes = None, {}, [], []
            try:
                draft = parse_draft(raw)
            except ValueError as exc:
                draft = None
                problems = [f"Ответ не в нужном формате: {exc}"]
            if draft is not None:
                task, problems, fixes = build_task(draft, req, task_type, time_limit, await self._new_task_id())
                if task is not None and not problems:
                    test_problems, tests = await check_tests(task, self._runner)
                    problems += test_problems
            report.append({"attempt": attempt + 1, "problems": problems, "fixes": fixes, "tests": tests})
            await self._update(
                job_id, report=list(report), draft=draft.model_dump() if draft else {"raw": raw[:20000]}
            )

            if not problems:
                async with self._sessions() as s:
                    task.status = "review"  # к кандидатам — только после проверки экспертом на решаемость
                    s.add(TaskRow(id=task.id, data=task.model_dump()))
                    job = await s.get(TaskGeneration, job_id)
                    job.status = "done"
                    job.task_id = task.id
                    job.finished_at = utcnow()
                    await s.commit()
                log.info("generated task %s for %s · %s", task.id, req.categories, req.grades)
                return

            messages = messages + [
                Message(role="assistant", content=raw),
                Message(
                    role="user",
                    content="Черновик не прошёл проверки:\n- "
                    + "\n- ".join(problems)
                    + "\nИсправь и пришли задачу целиком в том же формате: === META ===, затем === FILE … === на каждый файл.",
                ),
            ]

        await self._update(
            job_id,
            status="failed",
            error=f"Черновик не прошёл проверки за {self._fix_attempts + 1} попыток",
            finished_at=utcnow(),
        )

    async def _new_task_id(self) -> str:
        """Номер варианта, как на экране теста: «Вариант #V1-0D8F»."""
        async with self._sessions() as s:
            while True:
                task_id = f"V1-{secrets.token_hex(2).upper()}"
                if await s.get(TaskRow, task_id) is None:
                    return task_id

    async def _update(self, job_id: str, **fields: Any) -> None:
        async with self._sessions() as s:
            job = await s.get(TaskGeneration, job_id)
            if job is None:
                return
            for key, value in fields.items():
                setattr(job, key, value)
            await s.commit()


def _job_view(job: TaskGeneration) -> dict[str, Any]:
    return {
        "id": job.id,
        "status": job.status,
        "request": job.request,
        "task_id": job.task_id,
        "error": job.error or None,
        "report": job.report or [],
        "draft": job.draft,
        "created_at": job.created_at.isoformat() + "Z" if job.created_at else None,
        "finished_at": job.finished_at.isoformat() + "Z" if job.finished_at else None,
    }
