import asyncio
import contextlib
from typing import Any, Literal

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field, field_validator, model_validator

from app.generation import GenerationRequest
from app.service import BadRequest, NotFound
from app.tasks import Grade, Task, normalize_category, task_view

router = APIRouter()


# --- схемы запросов и ответов (попадают в OpenAPI) ---


class StartAttempt(BaseModel):
    """Тест на категорию и грейд: либо конкретная задача (task_id), либо случайная подходящая."""

    # Авторизация живёт в основной части платформы; сюда приходит уже известный id кандидата.
    candidate_id: str
    task_id: str | None = None
    category: str | None = Field(default=None, description="Направление как на сайте: «Backend» или «backend»")
    level: Grade | None = Field(default=None, description="Грейд, на который тест: intern | junior | middle | senior")

    @field_validator("category")
    @classmethod
    def _category(cls, value: str | None) -> str | None:
        return None if value is None else normalize_category(value)

    @model_validator(mode="after")
    def _task_or_filters(self) -> "StartAttempt":
        if not self.task_id and not (self.category and self.level):
            raise ValueError("нужен task_id или пара category + level")
        return self


class TaskOut(BaseModel):
    id: str = Field(description="Номер варианта задачи")
    status: str = Field(description="review — ждёт эксперта; published — выдаётся кандидатам; rejected — отклонена")
    title: str
    type: str
    categories: list[str]
    grades: list[str]
    time_limit_min: int
    statement: str
    assessed: list[str] = Field(description="«Что оценивается» — показывается кандидату")
    has_tests: bool


class GenerationReportItem(BaseModel):
    attempt: int
    problems: list[str] = Field(description="Что не прошло проверки; пусто — черновик принят")
    fixes: list[str] = Field(default=[], description="Что платформа поправила в черновике сама")
    tests: dict[str, Any] = Field(description="Прогон тестов на стартовом коде и на эталоне")


class GenerationOut(BaseModel):
    id: str
    status: str = Field(description="pending | running | done | failed")
    request: dict[str, Any]
    task_id: str | None = Field(description="Задача в банке, когда status=done")
    error: str | None
    report: list[GenerationReportItem]
    draft: dict[str, Any] | None = Field(description="Последний черновик модели — посмотреть, что не прошло")
    created_at: str | None
    finished_at: str | None


class EditOut(BaseModel):
    id: int
    path: str
    summary: str
    status: str = Field(description="pending | accepted | rejected | stale")
    reason: str
    diff: str = Field(description="unified diff относительно версии файла, от которой считалась правка")
    added: int
    removed: int
    is_new_file: bool
    created_at: str | None


class StatsOut(BaseModel):
    assistant_requests: int = Field(description="Сколько раз кандидат обращался к ассистенту")
    manual_edits: int = Field(description="Сколько раз кандидат сохранял файл вручную")
    edits_proposed: int
    edits_accepted: int
    edits_rejected: int
    test_runs: int
    tab_leaves: int = Field(default=0, description="Сколько раз кандидат уходил со вкладки теста")


class ChatItem(BaseModel):
    role: str = Field(description="user | assistant | error")
    text: str
    edit_ids: list[int] = []
    at: str | None


class AttemptOut(BaseModel):
    id: str
    candidate_id: str
    category: str = Field(description="На какую категорию тест — «Backend»")
    level: str = Field(description="На какой грейд тест — «senior»")
    status: str = Field(description="active | submitted | expired")
    grading_status: str = Field(description="not_submitted | pending | running | done | failed")
    started_at: str | None
    deadline_at: str | None
    submitted_at: str | None
    remaining_s: int
    task: TaskOut
    files: dict[str, str]
    edits: list[EditOut]
    stats: StatsOut
    chat: list[ChatItem]


class EventOut(BaseModel):
    id: int
    type: str
    payload: dict[str, Any]
    at: str | None


class AssistantIn(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)


class AssistantOut(BaseModel):
    reply: str
    edits: list[EditOut] = Field(description="Правки, которые ассистент предложил в этом ответе")


class SaveFileIn(BaseModel):
    path: str
    content: str


class SaveFileOut(BaseModel):
    changed: bool


class RejectIn(BaseModel):
    reason: str = ""


class TestRunOut(BaseModel):
    passed: bool
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    output: str


class SubmitOut(BaseModel):
    status: str
    submitted_at: str | None


class CriterionResultOut(BaseModel):
    id: str
    text: str
    kind: str = Field(description="solution — про решение, process — про ход работы")
    check: str = Field(default="judge", description="judge — вердикт судьи; tests — засчитано платформой по прогону автотестов")
    points: int
    partial_points: int | None
    verdict: str = Field(description="yes | partial | no — итог по большинству прогонов")
    earned: int
    comment: str
    evidence: str = Field(description="Цитата из материалов, подтверждающая вердикт; пусто, если не засчитан")
    runs: list[str] = Field(description="Засчитанный вердикт в каждом прогоне судьи")
    said: list[str] = Field(default=[], description="Что сказал судья в каждом прогоне, до проверки цитаты")
    unconfirmed: int = Field(default=0, description="В скольких прогонах судья сказал «да» или «частично», но цитата не нашлась в материалах")
    ai_verdict: str | None = Field(default=None, description="Вердикт ИИ, если человек его исправил")
    corrected: bool = Field(default=False, description="Вердикт исправлен человеком")


class ThresholdOut(BaseModel):
    grade: str
    min_score: int = Field(description="Порог в баллах из 100")
    required: list[str]
    reached: bool


class RunOut(BaseModel):
    run: int
    score_100: int | None = None
    score: int
    grade: str | None


class TestsOut(BaseModel):
    passed: bool
    output: str


class FinalOut(BaseModel):
    score: int = Field(description="Итоговый балл из 100")
    passed: bool = Field(description="Тест на этот уровень пройден — грейд меняется")
    at: str | None


class ViolationsOut(BaseModel):
    count: int = Field(description="Сколько раз кандидат уходил со вкладки теста; любой уход — нарушение")
    away_s: int = Field(description="Сколько секунд всего был не на вкладке")


class ReviewOut(BaseModel):
    reviewer: str
    annulled: bool = Field(description="Попытка аннулирована: её грейд снят, тесты кандидата заморожены")
    comment: str
    at: str | None


class CorrectionOut(BaseModel):
    reviewer: str
    at: str | None
    score: int = Field(description="Балл из 100 после правки человека; оценка ИИ — в ai_score")
    changed: list[str] = Field(description="id критериев, вердикты которых исправлены")


class GradingOut(BaseModel):
    """Результат проверки: оценка LLM-судьи и постобработка. Поля с баллами заполнены при status=done."""

    attempt_id: str
    status: str = Field(description="not_submitted | pending | running | done | failed")
    error: str | None = None
    finished_at: str | None = None
    ai_score: int | None = Field(default=None, description="Балл из 100 — «ИИ 82/100»")
    final: FinalOut | None = Field(default=None, description="Итог теста; null — оценка ещё не готова")
    score: int | None = Field(default=None, description="Сырые баллы рубрики")
    max_score: int | None = None
    grade: str | None = Field(default=None, description="Высший пройденный порог; null — ни один не пройден")
    passed: bool | None = None
    level_confirmed: bool | None = Field(default=None, description="Грейд не ниже того, на который рассчитана задача")
    unstable: bool | None = Field(default=None, description="Прогоны судьи дали разный грейд — засчитан нижний")
    criteria: list[CriterionResultOut] = []
    thresholds: list[ThresholdOut] = []
    runs: list[RunOut] = []
    failed_runs: int | None = None
    tests: TestsOut | None = None
    violations: ViolationsOut | None = None
    review: ReviewOut | None = Field(default=None, description="Решение человека по попытке; null — ещё не принималось")
    needs_review: bool = Field(default=False, description="Есть нарушения, а человек ещё не решил")
    correction: CorrectionOut | None = Field(default=None, description="Правка человека: итог (final, criteria, thresholds) — уже с ней")


class FocusIn(BaseModel):
    left: bool = Field(description="true — кандидат ушёл со вкладки теста, false — вернулся")


class AttemptReviewIn(BaseModel):
    """Человек решил по помеченной попытке: аннулировать или засчитать."""

    reviewer: str = Field(min_length=1, max_length=120)
    annul: bool
    comment: str = Field(default="", description="Почему аннулирована или почему засчитана")
    verdicts: dict[str, Literal["yes", "partial", "no"]] = Field(
        default_factory=dict,
        description="Исправленные вердикты по критериям: id → yes | partial | no. Пусто — оценка ИИ подтверждена как есть",
    )


class ReviewQueueItemOut(BaseModel):
    attempt_id: str
    candidate_id: str
    category: str
    level: str
    task_id: str
    task_title: str
    submitted_at: str | None
    ai_score: int
    final: FinalOut | None
    violations: ViolationsOut
    needs_review: bool = Field(description="Помечена за уход со вкладки, а человек ещё не решил")
    review: ReviewOut | None


class TaskReviewIn(BaseModel):
    """Эксперт прорешал задачу: решаема ли она человеком в отведённое время."""

    expert: str = Field(min_length=1, max_length=120)
    approved: bool
    comment: str = Field(default="", description="Почему отклонена или что заметил при решении")


class LevelTestOut(BaseModel):
    level: str
    available: bool
    reason: str | None = Field(description="Почему недоступен: текущий грейд, раз в 3 месяца, повтор через 30 дней…")
    available_from: str | None


class GradeStatusOut(BaseModel):
    candidate_id: str
    category: str
    grade: str | None = Field(description="Подтверждённый грейд; null — ещё нет")
    score: int | None = Field(description="Балл теста, которым подтверждён грейд — «Тест 86/100»")
    confirmed_at: str | None
    next_change_at: str | None = Field(description="«Смена грейда: доступно с …»")
    change_available: bool
    frozen_until: str | None = Field(default=None, description="Попытку аннулировали — тесты недоступны до этой даты")
    tests: list[LevelTestOut] = Field(description="Кнопки «Тест на Senior / на Junior»")


class HistoryItemOut(BaseModel):
    attempt_id: str
    task_id: str
    task_title: str
    category: str
    level: str
    started_at: str | None
    submitted_at: str | None
    status: str
    grading_status: str
    ai_score: int | None
    final: FinalOut | None
    tab_leaves: int = 0
    annulled: bool = False
    reviewed: bool = Field(default=False, description="Оценку ИИ смотрел человек: подтвердил, исправил или аннулировал")


# --- REST ---


def _service(request: Request):
    return request.app.state.service


def _category(value: str) -> str:
    try:
        return normalize_category(value)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc


@router.get("/health", tags=["служебное"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/tasks", response_model=list[TaskOut], tags=["задачи"])
async def list_tasks(
    request: Request,
    category: str | None = None,
    grade: str | None = None,
    status: Literal["review", "published", "rejected"] | None = None,
):
    """Банк задач; фильтры по категории, грейду и статусу. status=review — очередь эксперта. Новые сверху."""
    category = _category(category) if category else None
    return [task_view(t).model_dump() for t in await _service(request).list_tasks(category, grade, status)]


@router.post("/tasks/{task_id}/review", response_model=Task, tags=["задачи"])
async def review_task(task_id: str, body: TaskReviewIn, request: Request):
    """Эксперт проверил задачу на решаемость: approved=true — задача выдаётся кандидатам, false — нет.
    Прорешать задачу на проверке эксперт может сам: POST /attempts с её task_id."""
    return await _service(request).review_task(task_id, body.expert, body.approved, body.comment)


@router.get("/tasks/{task_id}", response_model=Task, tags=["задачи"])
async def get_task(task_id: str, request: Request):
    """Задача целиком: стартовые файлы, эталон, критерии и пороги. Для банка задач, не для кандидата."""
    return await _service(request).get_task(task_id)


@router.post("/tasks/generate", response_model=GenerationOut, status_code=status.HTTP_202_ACCEPTED, tags=["задачи"])
async def generate_task(body: GenerationRequest, request: Request):
    """Сгенерировать задачу под категории и грейды. Идёт в фоне — статус в GET /tasks/generations/{id}.
    Модель пишет условие, файлы, тесты, эталон, критерии и пороги; платформа проверяет их и при ошибках
    просит модель исправить. Прошедшая проверки задача сразу попадает в банк."""
    return await request.app.state.generator.create(body)


@router.get("/tasks/generations/{generation_id}", response_model=GenerationOut, tags=["задачи"])
async def get_generation(generation_id: str, request: Request):
    return await request.app.state.generator.job(generation_id)


@router.post("/attempts", response_model=AttemptOut, status_code=status.HTTP_201_CREATED, tags=["попытка"])
async def start_attempt(body: StartAttempt, request: Request):
    """Старт теста на категорию и грейд: запускается таймер, файлы задачи копируются в попытку.
    Без task_id задача выбирается случайно среди подходящих, сначала из нерешённых кандидатом.
    С task_id категорию и грейд можно не указывать, если у задачи они единственные.
    409 — тест на этот грейд сейчас недоступен (текущий грейд, смена раз в 3 месяца, повтор через 30 дней)."""
    service = _service(request)
    category, level = body.category, body.level
    if body.task_id:
        task = await service.get_task(body.task_id)
        if category is None and len(task.categories) == 1:
            category = task.categories[0]
        if level is None and len(task.grades) == 1:
            level = task.grades[0]
        if category is None or level is None:
            raise BadRequest(f"У задачи несколько категорий или грейдов — укажите category и level: {task.categories} · {task.grades}")
    await request.app.state.grades.check_can_start(body.candidate_id, category, level)
    task_id = body.task_id or await service.pick_task(body.candidate_id, category, level)
    attempt_id = await service.start(task_id, body.candidate_id, category, level)
    return await service.state(attempt_id)


@router.get("/attempts/{attempt_id}", response_model=AttemptOut, tags=["попытка"])
async def get_attempt(attempt_id: str, request: Request):
    """Полное состояние: условие, файлы, правки, лента чата, счётчики, остаток времени."""
    return await _service(request).state(attempt_id)


@router.get("/attempts/{attempt_id}/events", response_model=list[EventOut], tags=["попытка"])
async def get_events(attempt_id: str, request: Request, after_id: int = 0):
    """Журнал сессии — то, по чему потом оценивается процесс."""
    return await _service(request).events(attempt_id, after_id)


@router.post("/attempts/{attempt_id}/assistant", response_model=AssistantOut, tags=["ассистент"])
async def ask_assistant(attempt_id: str, body: AssistantIn, request: Request):
    """Сообщение ассистенту. Ответ приходит, когда ассистент закончит; промежуточные шаги — в WebSocket.

    409 — ассистент ещё отвечает на предыдущее сообщение или попытка закрыта; 502 — модель недоступна.
    """
    return await request.app.state.assistant.reply(attempt_id, body.text)


@router.put("/attempts/{attempt_id}/files", response_model=SaveFileOut, tags=["файлы"])
async def save_file(attempt_id: str, body: SaveFileIn, request: Request):
    """Ручная правка кандидата. Непринятые правки ассистента к этому файлу становятся stale."""
    return await _service(request).save_file(attempt_id, body.path, body.content)


@router.post("/attempts/{attempt_id}/edits/{edit_id}/accept", response_model=EditOut, tags=["файлы"])
async def accept_edit(attempt_id: str, edit_id: int, request: Request):
    """Применить правку ассистента. 409, если файл успел измениться."""
    return await _service(request).decide_edit(attempt_id, edit_id, accept=True)


@router.post("/attempts/{attempt_id}/edits/{edit_id}/reject", response_model=EditOut, tags=["файлы"])
async def reject_edit(attempt_id: str, edit_id: int, request: Request, body: RejectIn | None = None):
    return await _service(request).decide_edit(attempt_id, edit_id, accept=False, reason=(body.reason if body else ""))


@router.post("/attempts/{attempt_id}/tests", response_model=TestRunOut, tags=["файлы"])
async def run_tests(attempt_id: str, request: Request):
    result = await _service(request).run_tests(attempt_id, by="candidate")
    return TestRunOut(
        passed=result.passed,
        exit_code=result.exit_code,
        timed_out=result.timed_out,
        duration_ms=result.duration_ms,
        output=result.summary(),
    )


@router.post("/attempts/{attempt_id}/focus", tags=["попытка"])
async def focus(attempt_id: str, body: FocusIn, request: Request) -> dict[str, bool]:
    """Кандидат ушёл со вкладки теста или вернулся. Уход запрещён: любой отмечается в результате,
    попытку помечаем, решает человек. 409 — тест уже закончен."""
    return await _service(request).record_focus(attempt_id, body.left)


@router.post("/attempts/{attempt_id}/submit", response_model=SubmitOut, tags=["попытка"])
async def submit(attempt_id: str, request: Request):
    """Сдать решение. Проверка запускается сразу в фоне; когда закончится — событие grading.completed в WebSocket."""
    result = await _service(request).submit(attempt_id)
    request.app.state.grader.schedule(attempt_id)
    return result


@router.get("/attempts/{attempt_id}/result", response_model=GradingOut, tags=["проверка"])
async def get_result(attempt_id: str, request: Request):
    """Результат теста: балл из 100, вердикты по критериям с цитатами, итог — оценка LLM после постобработки.
    Один и тот же для кандидата и работодателя; разграничение доступа — в основной части платформы."""
    return await request.app.state.grades.result(attempt_id)


@router.get("/candidates/{candidate_id}/grade", response_model=GradeStatusOut, tags=["грейд"])
async def grade_status(candidate_id: str, category: str, request: Request):
    """Экран «Грейд и тесты»: текущий грейд в категории, балл, когда можно менять, какие тесты доступны."""
    return await request.app.state.grades.status(candidate_id, _category(category))


@router.get("/candidates/{candidate_id}/attempts", response_model=list[HistoryItemOut], tags=["грейд"])
async def test_history(candidate_id: str, request: Request):
    """«История тестов»: тест, балл, итог. Новые сверху."""
    return await request.app.state.grades.history(candidate_id)


@router.post("/attempts/{attempt_id}/review", response_model=GradingOut, tags=["проверка"])
async def review_attempt(attempt_id: str, body: AttemptReviewIn, request: Request):
    """Решение человека по попытке. annul=true — аннулирована: грейд, полученный ею, снимается
    (возвращается прежний), тесты кандидата заморожены на 30 дней. verdicts — исправленные вердикты по критериям:
    балл пересчитывается, итог теста и грейд — по исправленным. Ничего не передано — оценка ИИ подтверждена.
    Решение принимается один раз; 409 — тест ещё идёт, оценка не готова или решение уже есть."""
    return await request.app.state.grades.review(attempt_id, body.reviewer, body.annul, body.comment, body.verdicts)


@router.get("/reviews", response_model=list[ReviewQueueItemOut], tags=["проверка"])
async def review_queue(request: Request):
    """Очередь «Проверки оценок»: сданные попытки с готовой оценкой ИИ. Сначала помеченные за уход со вкладки
    и ещё не решённые, потом остальные без решения, потом решённые; внутри — новые сверху."""
    return await request.app.state.grades.queue()


@router.post("/attempts/{attempt_id}/grade", status_code=status.HTTP_202_ACCEPTED, tags=["проверка"])
async def regrade(attempt_id: str, request: Request) -> dict[str, str]:
    """Перепроверить завершённую попытку — например, после правки рубрики или промпта судьи."""
    await request.app.state.grader.request(attempt_id)
    return {"status": "scheduled"}


# --- WebSocket: живые события попытки ---


@router.websocket("/attempts/{attempt_id}/ws")
async def attempt_events(websocket: WebSocket, attempt_id: str):
    """Сервер → клиент. Сообщения:
    {"type": "assistant.status", "state": "started"} — ассистент принял сообщение;
    {"type": "assistant.status", "state": "generating"} — модель генерирует;
    {"type": "assistant.status", "state": "tool", "tool": "read_file", "path": "limiter.py"} — работает с файлами;
    {"type": "assistant.delta", "text": "..."} — очередной кусок ответа, склеивать по порядку;
    {"type": "assistant.status", "state": "idle"} — ответ закончен;
    {"type": "event", "event": {...}} — событие журнала: правка предложена, тесты запущены,
        итоговый ответ (assistant.message, его текст заменяет склеенные куски) и т. д.
    """
    service = websocket.app.state.service
    try:
        await service.ensure_exists(attempt_id)
    except NotFound:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    bus = websocket.app.state.bus
    queue = bus.subscribe(attempt_id)

    async def forward():
        while True:
            await websocket.send_json(await queue.get())

    async def until_disconnect():
        with contextlib.suppress(WebSocketDisconnect):
            while True:
                await websocket.receive_text()

    tasks = [asyncio.create_task(forward()), asyncio.create_task(until_disconnect())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        bus.unsubscribe(attempt_id, queue)
