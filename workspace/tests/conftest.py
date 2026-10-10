import asyncio
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import Base, make_engine
from app.llm.balancer import ChannelLimiter
from app.llm.gateway import Channel, Gateway
from app.llm.types import ChatRequest, ChatResult, Message, ToolCall
from app.main import create_app

FIXED_DEDUP = (Path(__file__).parent.parent / "tasks/placeholder-dedup/files/dedup.py").read_text(encoding="utf-8").replace(
    "        total += event[\"amount\"]", "        seen.add(event[\"id\"])\n        total += event[\"amount\"]"
)


class ScriptedModel:
    """Модель, которая отвечает заранее заданными шагами и запоминает запросы."""

    def __init__(self, *steps: ChatResult):
        self.steps = list(steps)
        self.requests: list[ChatRequest] = []

    async def chat(self, req: ChatRequest, on_delta=None) -> ChatResult:
        self.requests.append(req)
        if not self.steps:
            return text("ок")
        return self.steps.pop(0)


def text(content: str) -> ChatResult:
    return ChatResult(message=Message(role="assistant", content=content))


def call(name: str, **arguments) -> ChatResult:
    return ChatResult(message=Message(role="assistant", tool_calls=[ToolCall(id=f"c-{name}", name=name, arguments=arguments)]))


def scripted_gateway(model) -> Gateway:
    return Gateway({"main": Channel("main", model, "m", ChannelLimiter("main", 1))}, routes={"assistant": "main"}, fallback="main")


@pytest.fixture
def settings(tmp_path) -> Settings:
    # TEST_DATABASE_URL=postgresql+asyncpg://… — прогнать тесты на Postgres; база очищается перед каждым тестом
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        asyncio.run(_drop_tables(url))
    return Settings(database_url=url or f"sqlite+aiosqlite:///{tmp_path / 'test.db'}", llm_mode="stub", sandbox="local")


def wait_final(client: TestClient, attempt_id: str, timeout=10.0) -> dict:
    """Дождаться итога теста вместе с его последствиями: смена грейда пишется сразу после оценки,
    в одном шаге с событием result.final — по нему и ждём."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(e["type"] == "result.final" for e in client.get(f"/attempts/{attempt_id}/events").json()):
            return client.get(f"/attempts/{attempt_id}/result").json()
        time.sleep(0.05)
    raise AssertionError("не дождались итога теста")


def run_sql(settings: Settings, sql: str, **params) -> None:
    """Подправить данные в обход API (например, «перемотать» время) — на SQLite и на Postgres."""
    from sqlalchemy import text as sql_text

    async def run() -> None:
        engine = make_engine(settings.database_url)
        async with engine.begin() as conn:
            await conn.execute(sql_text(sql), params)
        await engine.dispose()

    asyncio.run(run())


async def _drop_tables(url: str) -> None:
    from app import models  # noqa: F401  регистрирует таблицы в Base.metadata

    engine = make_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def make_client(settings):
    clients = []

    def factory(model=None) -> TestClient:
        app = create_app(settings, gateway=scripted_gateway(model) if model else None)
        client = TestClient(app)
        client.__enter__()
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.__exit__(None, None, None)


def start(client: TestClient, candidate_id: str = "cand-1", level: str = "middle") -> dict:
    resp = client.post("/attempts", json={"task_id": "V1-7C2A", "candidate_id": candidate_id, "level": level})
    assert resp.status_code == 201, resp.text
    return resp.json()


def wait_result(client: TestClient, attempt_id: str, until=lambda r: r["status"] in ("done", "failed"), timeout=10.0) -> dict:
    deadline = time.monotonic() + timeout
    result = None
    while time.monotonic() < deadline:
        result = client.get(f"/attempts/{attempt_id}/result").json()
        if until(result):
            return result
        time.sleep(0.05)
    raise AssertionError(f"не дождались результата: {result}")
