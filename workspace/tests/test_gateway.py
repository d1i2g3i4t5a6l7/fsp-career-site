import pytest
from pydantic import BaseModel

from app.llm.balancer import ChannelLimiter
from app.llm.gateway import Channel, Gateway
from app.llm.types import ChatRequest, ChatResult, InvalidResponse, Message, ProviderUnavailable, RateLimited


class Scripted:
    """Провайдер, который отдаёт заранее заданные ответы или исключения по очереди."""

    def __init__(self, *steps):
        self.steps = list(steps)
        self.requests: list[ChatRequest] = []

    async def chat(self, req: ChatRequest, on_delta=None) -> ChatResult:
        self.requests.append(req)
        step = self.steps.pop(0)
        if isinstance(step, tuple):  # (кусок текста, исключение): упасть посреди потока
            await on_delta(step[0])
            raise step[1]
        if isinstance(step, Exception):
            raise step
        return ChatResult(message=Message(role="assistant", content=step))


async def _no_sleep(_):
    return None


def _gateway(*channels: tuple[str, Scripted], journal=None, fallback=None) -> Gateway:
    chans = {name: Channel(name, provider, f"{name}-model", ChannelLimiter(name, 1)) for name, provider in channels}
    return Gateway(chans, routes={"assistant": channels[0][0]}, fallback=fallback, max_retries=2, journal=journal, sleep=_no_sleep)


USER = [Message(role="user", content="привет")]


async def test_retries_after_rate_limit_and_journals_each_call():
    provider = Scripted(RateLimited("429", retry_after=0.001), "ok")
    entries = []

    async def journal(entry):
        entries.append(entry)

    gw = _gateway(("main", provider), journal=journal)
    result = await gw.chat("assistant", USER, attempt_id="a1", prompt_version="v1")
    assert result.message.content == "ok"
    assert [e["status"] for e in entries] == ["rate_limited", "ok"]
    assert entries[1]["attempt_id"] == "a1" and entries[1]["model"] == "main-model"


async def test_falls_back_when_channel_unavailable():
    broken = Scripted(*(ProviderUnavailable("down") for _ in range(3)))
    backup = Scripted("from backup")
    gw = _gateway(("lightning", broken), ("gigachat", backup), fallback="gigachat")
    result = await gw.chat("assistant", USER)
    assert result.message.content == "from backup"
    assert len(broken.requests) == 3


async def test_unconfigured_route_uses_fallback():
    backup = Scripted("ok")
    gw = Gateway(
        {"gigachat": Channel("gigachat", backup, "m", ChannelLimiter("g", 1))},
        routes={"customer": "lightning"},
        fallback="gigachat",
    )
    assert (await gw.chat("customer", USER)).message.content == "ok"


class Reply(BaseModel):
    answer: str


async def test_chat_json_asks_model_to_fix_invalid_output():
    provider = Scripted("не json", '```json\n{"answer": "да"}\n```')
    gw = _gateway(("main", provider))
    reply = await gw.chat_json("assistant", [Message(role="system", content="sys"), *USER], Reply)
    assert reply.answer == "да"
    # схема дописана в системный промпт, во второй попытке модели показали её ошибку
    assert "JSON-схеме" in provider.requests[0].messages[0].content
    assert provider.requests[1].messages[-1].role == "user"


async def test_no_retry_or_fallback_after_candidate_saw_part_of_answer():
    broken = Scripted(("Сейчас посмо", ProviderUnavailable("обрыв")), "не должен вызываться")
    backup = Scripted("и этот тоже")
    gw = _gateway(("main", broken), ("gigachat", backup), fallback="gigachat")
    seen = []

    async def on_delta(chunk):
        seen.append(chunk)

    with pytest.raises(ProviderUnavailable):
        await gw.chat("assistant", USER, on_delta=on_delta)
    assert seen == ["Сейчас посмо"]
    assert len(broken.requests) == 1 and not backup.requests


async def test_status_reported_when_model_starts():
    statuses = []
    gw = _gateway(("main", Scripted("ok")))
    await gw.chat("assistant", USER, on_status=statuses.append)
    assert statuses == [{"state": "generating"}]


async def test_chat_json_gives_up():
    provider = Scripted("нет", "нет", "нет")
    gw = _gateway(("main", provider))
    with pytest.raises(InvalidResponse):
        await gw.chat_json("assistant", USER, Reply)
