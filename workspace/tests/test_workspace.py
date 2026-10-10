import asyncio
from datetime import timedelta

import pytest

from app.assistant import Assistant, Busy, compact
from app.bus import EventBus
from app.db import create_tables, make_engine, make_sessions, utcnow
from app.llm.types import ChatRequest, ChatResult, Message, ToolCall
from app.main import SERVICE_ROOT
from app.models import Attempt
from app.sandbox import LocalRunner
from app.service import AttemptClosed, AttemptService
from app.tasks import load_tasks_from_dir
from tests.conftest import FIXED_DEDUP, ScriptedModel, call, scripted_gateway, start, text


def test_candidate_fixes_bug_with_assistant(make_client):
    model = ScriptedModel(
        call("read_file", path="dedup.py"),
        call("propose_edit", path="dedup.py", content=FIXED_DEDUP, summary="Запоминаем обработанные id"),
        text("Предложил правку: добавил seen.add."),
    )
    client = make_client(model)
    attempt = start(client)
    aid = attempt["id"]
    assert attempt["task"]["id"] == "V1-7C2A"
    assert set(attempt["files"]) == {"dedup.py", "test_dedup.py", "run_tests.py"}
    assert 25 * 60 < attempt["remaining_s"] <= 30 * 60  # тест на грейд — 30 минут

    assert client.post(f"/attempts/{aid}/tests").json()["passed"] is False

    resp = client.post(f"/attempts/{aid}/assistant", json={"text": "Почему платёж считается дважды? Почини."})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reply"].startswith("Предложил правку")
    [edit] = body["edits"]
    assert edit["status"] == "pending" and "+        seen.add" in edit["diff"]
    # read_file вернул модели актуальный файл, а правка до принятия файл не меняет
    assert "seen = set()" in model.requests[1].messages[-1].content
    assert client.get(f"/attempts/{aid}").json()["files"]["dedup.py"] != FIXED_DEDUP

    assert client.post(f"/attempts/{aid}/edits/{edit['id']}/accept").json()["status"] == "accepted"
    run = client.post(f"/attempts/{aid}/tests").json()
    assert run["passed"] is True, run["output"]

    # ассистент узнаёт о действиях кандидата из уведомлений в следующем сообщении
    client.post(f"/attempts/{aid}/assistant", json={"text": "Спасибо"})
    last_user = model.requests[-1].messages[-1].content
    assert "[Событие: кандидат принял правку #1 в dedup.py]" in last_user
    assert "[Событие: кандидат запустил тесты: прошли]" in last_user

    state = client.get(f"/attempts/{aid}").json()
    assert state["stats"] == {
        "assistant_requests": 2,
        "manual_edits": 0,
        "edits_proposed": 1,
        "edits_accepted": 1,
        "edits_rejected": 0,
        "test_runs": 2,
        "tab_leaves": 0,
    }
    assert [c["role"] for c in state["chat"]] == ["user", "assistant", "user", "assistant"]
    assert state["chat"][1]["edit_ids"] == [edit["id"]]

    assert client.post(f"/attempts/{aid}/submit").json()["status"] == "submitted"
    closed = client.post(f"/attempts/{aid}/assistant", json={"text": "ещё"})
    assert closed.status_code == 409


def test_reject_and_stale_edits_with_stub(make_client):
    client = make_client()  # заглушка LLM
    aid = start(client)["id"]

    first = client.post(f"/attempts/{aid}/assistant", json={"text": "исправь баг"}).json()
    [edit] = first["edits"]
    rejected = client.post(f"/attempts/{aid}/edits/{edit['id']}/reject", json={"reason": "это не исправляет баг"}).json()
    assert rejected["status"] == "rejected" and rejected["reason"] == "это не исправляет баг"

    second = client.post(f"/attempts/{aid}/assistant", json={"text": "исправь ещё раз"}).json()
    [edit2] = second["edits"]
    # кандидат сам поправил файл — правка ассистента устарела
    assert client.put(f"/attempts/{aid}/files", json={"path": "dedup.py", "content": FIXED_DEDUP}).json()["changed"]
    resp = client.post(f"/attempts/{aid}/edits/{edit2['id']}/accept")
    assert resp.status_code == 409
    state = client.get(f"/attempts/{aid}").json()
    assert [e["status"] for e in state["edits"]] == ["rejected", "stale"]
    assert state["stats"]["manual_edits"] == 1 and state["stats"]["edits_rejected"] == 1

    types = [e["type"] for e in client.get(f"/attempts/{aid}/events").json()]
    assert types.count("assistant.tool") == 2  # два read_file
    assert "edit.rejected" in types and "edit.stale" in types and "file.saved" in types


def test_bad_paths_and_unknown_attempt(make_client):
    client = make_client()
    aid = start(client)["id"]
    assert client.put(f"/attempts/{aid}/files", json={"path": "../evil.py", "content": "x"}).status_code == 400
    assert client.get("/attempts/nope").status_code == 404
    assert client.post("/attempts", json={"task_id": "nope", "candidate_id": "c"}).status_code == 404


def test_websocket_streams_answer_and_statuses(make_client):
    client = make_client()  # заглушка печатает ответ кусками
    aid = start(client)["id"]
    with client.websocket_connect(f"/attempts/{aid}/ws") as ws:
        reply = client.post(f"/attempts/{aid}/assistant", json={"text": "запусти тесты"}).json()["reply"]
        seen = []
        while not (seen and seen[-1] == {"type": "assistant.status", "state": "idle"}):
            seen.append(ws.receive_json())

    events = [m["event"]["type"] for m in seen if m["type"] == "event"]
    assert events == ["assistant.user_message", "tests.run", "assistant.message"]
    statuses = [m["state"] for m in seen if m["type"] == "assistant.status"]
    assert statuses == ["started", "generating", "tool", "generating", "idle"]
    assert {"type": "assistant.status", "state": "tool", "tool": "run_tests"} in seen
    deltas = [m["text"] for m in seen if m["type"] == "assistant.delta"]
    assert len(deltas) > 1 and "".join(deltas) == reply


def test_text_before_tool_call_is_part_of_reply(make_client):
    model = ScriptedModel(
        ChatResult(
            message=Message(role="assistant", content="Сейчас посмотрю файл.", tool_calls=[ToolCall(id="1", name="list_files")])
        ),
        text("Файлов три."),
    )
    client = make_client(model)
    aid = start(client)["id"]
    assert client.post(f"/attempts/{aid}/assistant", json={"text": "что тут?"}).json()["reply"] == (
        "Сейчас посмотрю файл.\n\nФайлов три."
    )


async def _service(tmp_path):
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'svc.db'}")
    await create_tables(engine)
    sessions = make_sessions(engine)
    await load_tasks_from_dir(SERVICE_ROOT / "tasks", sessions)
    return engine, sessions, AttemptService(sessions, LocalRunner(), EventBus())


async def test_second_message_while_busy_is_rejected(tmp_path):
    engine, _, service = await _service(tmp_path)
    release = asyncio.Event()

    class SlowModel:
        async def chat(self, req: ChatRequest, on_delta=None) -> ChatResult:
            await release.wait()
            return text("готово")

    assistant = Assistant(service, scripted_gateway(SlowModel()))
    aid = await service.start("V1-7C2A", "c", "Backend", "middle")
    first = asyncio.create_task(assistant.reply(aid, "первый"))
    await asyncio.sleep(0.05)
    with pytest.raises(Busy):
        await assistant.reply(aid, "второй")
    release.set()
    assert (await first)["reply"] == "готово"
    await engine.dispose()


async def test_timer_closes_attempt(tmp_path):
    engine, sessions, service = await _service(tmp_path)
    aid = await service.start("V1-7C2A", "c", "Backend", "middle")
    async with sessions() as s:
        attempt = await s.get(Attempt, aid)
        attempt.deadline_at = utcnow() - timedelta(seconds=1)
        await s.commit()
    with pytest.raises(AttemptClosed, match="Время вышло"):
        await service.save_file(aid, "dedup.py", "x")
    assert (await service.state(aid))["status"] == "expired"
    await engine.dispose()


async def test_step_limit_forces_text_answer(tmp_path):
    engine, _, service = await _service(tmp_path)
    model = ScriptedModel(*(call("list_files") for _ in range(10)))
    assistant = Assistant(service, scripted_gateway(model), max_steps=2)
    aid = await service.start("V1-7C2A", "c", "Backend", "middle")
    result = await assistant.reply(aid, "покажи файлы")
    assert result["reply"]  # на последнем шаге берётся текст, даже если модель снова зовёт инструмент
    assert len(model.requests) == 3
    assert model.requests[-1].messages[-1].content.startswith("[Система: лимит шагов")
    await engine.dispose()


async def test_repeated_identical_calls_are_cut_off(tmp_path):
    """Живой GigaChat зацикливался на run_tests: одинаковый вызов исполняется не больше двух раз,
    после двух заблокированных повторов модель обязана ответить текстом."""
    engine, _, service = await _service(tmp_path)
    model = ScriptedModel(*(call("run_tests") for _ in range(30)))
    assistant = Assistant(service, scripted_gateway(model), max_steps=25)
    aid = await service.start("V1-7C2A", "c", "Backend", "middle")
    result = await assistant.reply(aid, "запусти тесты")
    events = [e["type"] for e in await service.events(aid)]
    assert events.count("tests.run") == 2
    assert len(model.requests) == 5  # 2 запуска + 2 заблокированных повтора + финальный ответ
    assert model.requests[-1].messages[-1].content.startswith("[Система: лимит шагов")
    assert result["reply"]
    await engine.dispose()


def test_compact_trims_old_heavy_messages():
    big = "x" * 1000
    history = [Message(role="user", content="u")]
    history.append(Message(role="assistant", tool_calls=[ToolCall(id="1", name="propose_edit", arguments={"path": "a", "content": big})]))
    history.append(Message(role="tool", tool_call_id="1", name="propose_edit", content=big))
    history += [Message(role="user", content=f"m{i}") for i in range(12)]
    out = compact(history)
    assert out[1].tool_calls[0].arguments["content"] == "[содержимое правки опущено]"
    assert len(out[2].content) < 400
    assert out[-1].content == "m11"
