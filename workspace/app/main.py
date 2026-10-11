import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse

from app.api import router
from app.assistant import Assistant, AssistantFailed, Busy
from app.bus import EventBus
from app.config import Settings, get_settings
from app.db import create_tables, make_engine, make_sessions
from app.generation import TaskGenerator
from app.grades import GradeService
from app.grading import Grader
from app.llm.factory import build_gateway
from app.llm.gateway import Gateway
from app.models import LLMCall
from app.sandbox import LocalRunner, PistonRunner, Runner
from app.service import AttemptClosed, AttemptService, BadRequest, Conflict, NotFound
from app.tasks import load_tasks_from_dir

log = logging.getLogger(__name__)

SERVICE_ROOT = Path(__file__).resolve().parent.parent


def create_app(settings: Settings | None = None, *, gateway: Gateway | None = None, runner: Runner | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(settings.database_url)
        await create_tables(engine)
        sessions = make_sessions(engine)

        tasks_dir = Path(settings.tasks_dir)
        if not tasks_dir.is_absolute():
            tasks_dir = SERVICE_ROOT / tasks_dir
        loaded = await load_tasks_from_dir(tasks_dir, sessions)
        log.info("loaded %d tasks from %s", loaded, tasks_dir)

        async def journal(entry: dict) -> None:
            async with sessions() as s:
                s.add(LLMCall(**entry))
                await s.commit()

        if settings.sandbox == "piston":
            sandbox: Runner = PistonRunner(settings.piston_url, settings.sandbox_timeout_s)
        else:
            sandbox = LocalRunner(settings.sandbox_timeout_s)

        bus = EventBus()
        llm = gateway or build_gateway(settings, journal)
        service = AttemptService(sessions, runner or sandbox, bus)
        grades = GradeService(
            sessions,
            bus,
            cooldown_days=settings.grade_change_cooldown_days,
            retry_days=settings.same_level_retry_days,
            freeze_days=settings.annul_freeze_days,
        )
        grader = Grader(sessions, llm, runner or sandbox, bus, settings.grader_runs, on_done=grades.on_ai_done)
        await grader.recover()
        generator = TaskGenerator(
            sessions,
            llm,
            runner or sandbox,
            fix_attempts=settings.task_gen_fix_attempts,
            packages=settings.sandbox_packages,
        )
        await generator.recover()
        app.state.generator = generator
        app.state.bus = bus
        app.state.service = service
        app.state.assistant = Assistant(service, llm, settings.assistant_max_steps)
        app.state.grader = grader
        app.state.grades = grades

        async def watchdog() -> None:
            """Закрывает попытки с вышедшим временем и отправляет на проверку всё завершённое и непроверенное."""
            while True:
                try:
                    await service.expire_overdue()
                    for attempt_id in await grader.ungraded():
                        grader.schedule(attempt_id)
                except Exception:
                    log.exception("watchdog iteration failed")
                await asyncio.sleep(settings.grading_poll_s)

        watchdog_task = asyncio.create_task(watchdog())
        yield
        watchdog_task.cancel()
        await asyncio.gather(watchdog_task, return_exceptions=True)
        # Генерацию и проверки прерываем: после перезапуска они начнутся заново
        await generator.stop()
        await grader.stop()
        await engine.dispose()

    app = FastAPI(
        title="ФСП Карьера — рабочее место кандидата",
        version="0.1.0",
        description=(
            "Сессия решения задачи: файлы, ИИ-ассистент с правками на подтверждение, тесты в песочнице, журнал. "
            "После сдачи или конца времени — проверка LLM-судьёй по рубрике задачи и грейд.\n\n"
            "Адреса с пометкой «снаружи закрыто» — служебные: по ссылке сайта они отвечают 404 и работают только "
            "на самом сервере. Остальными пользуется сайт — их можно вызвать прямо отсюда, кнопкой «Try it out». "
            "Живые события попытки — WebSocket `/attempts/{attempt_id}/ws`: в Swagger его не видно, снаружи закрыт."
        ),
        # Swagger открывается и напрямую (localhost:8010/docs), и через сайт (/api/workspace/docs):
        # «Try it out» шлёт запросы туда же, откуда загружено описание API
        servers=[{"url": ".", "description": "этот же адрес"}],
        docs_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
    )
    app.include_router(router)

    @app.get("/docs", include_in_schema=False)
    async def swagger() -> HTMLResponse:
        # Адрес описания относительный: со страницы /api/workspace/docs он ведёт на /api/workspace/openapi.json
        return get_swagger_ui_html(openapi_url="openapi.json", title=app.title)

    errors = {
        NotFound: 404,
        BadRequest: 400,
        Conflict: 409,
        AttemptClosed: 409,
        Busy: 409,
        AssistantFailed: 502,
    }
    for exc_type, code in errors.items():
        app.add_exception_handler(exc_type, _handler(code))
    return app


def _handler(code: int):
    async def handle(request: Request, exc: Exception) -> JSONResponse:
        detail = "Ассистент сейчас недоступен, попробуйте ещё раз" if isinstance(exc, AssistantFailed) else str(exc)
        return JSONResponse(status_code=code, content={"detail": detail, "error": type(exc).__name__})

    return handle


app = create_app()
