import json
import time

import httpx
import pytest

from app.llm.providers.gigachat import GigaChatProvider, to_gigachat_messages
from app.llm.types import ChatRequest, Message, RateLimited, ToolCall, ToolSpec

AUTH_URL = "https://auth.test/api/v2/oauth"
BASE_URL = "https://api.test/v1"


def _provider(handler) -> GigaChatProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return GigaChatProvider("a2V5", auth_url=AUTH_URL, base_url=BASE_URL, client=client)


def _token_response(expires_at: float) -> httpx.Response:
    return httpx.Response(200, json={"access_token": "tok", "expires_at": expires_at})


async def test_function_call_roundtrip_and_token_reuse():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/api/v2/oauth":
            assert request.headers["Authorization"] == "Basic a2V5"
            assert request.headers["RqUID"]
            return _token_response((time.time() + 1800) * 1000)  # миллисекунды
        body = json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer tok"
        assert body["function_call"] == "auto"
        assert body["functions"][0]["name"] == "read_file"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "function_call": {"name": "read_file", "arguments": {"path": "a.py"}},
                            "functions_state_id": "state-1",
                        },
                        "finish_reason": "function_call",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3, "precached_prompt_tokens": 4},
            },
        )

    provider = _provider(handler)
    req = ChatRequest(
        scenario="assistant",
        model="GigaChat-3-Ultra",
        messages=[Message(role="user", content="прочитай")],
        tools=[ToolSpec(name="read_file", description="d", parameters={"type": "object", "properties": {}})],
    )
    first = await provider.chat(req)
    await provider.chat(req)

    call = first.message.tool_calls[0]
    assert (call.name, call.arguments) == ("read_file", {"path": "a.py"})
    assert first.message.provider_state == {"functions_state_id": "state-1"}
    assert first.usage.cached_tokens == 4
    assert sum(r.url.path == "/api/v2/oauth" for r in seen) == 1  # токен переиспользован


async def test_expires_at_in_seconds_is_understood():
    calls = {"oauth": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/oauth":
            calls["oauth"] += 1
            return _token_response(time.time() + 1800)  # секунды
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]})

    provider = _provider(handler)
    req = ChatRequest(scenario="x", model="m", messages=[Message(role="user", content="hi")])
    await provider.chat(req)
    await provider.chat(req)
    assert calls["oauth"] == 1


async def test_429_maps_to_rate_limited():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/oauth":
            return _token_response(time.time() + 1800)
        return httpx.Response(429, json={"status": 429, "message": "Too Many Requests"})

    provider = _provider(handler)
    with pytest.raises(RateLimited):
        await provider.chat(ChatRequest(scenario="x", model="m", messages=[Message(role="user", content="hi")]))


def _sse(*chunks) -> bytes:
    lines = [f"data: {json.dumps(c, ensure_ascii=False)}\n\n" for c in chunks]
    return ("".join(lines) + "data: [DONE]\n\n").encode()


async def test_streaming_text_and_function_call():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/oauth":
            return _token_response(time.time() + 1800)
        assert json.loads(request.content)["stream"] is True
        body = _sse(
            {"choices": [{"delta": {"role": "assistant", "content": "Сейчас "}, "index": 0}]},
            {"choices": [{"delta": {"content": "посмотрю."}, "index": 0}]},
            {
                "choices": [
                    {
                        "delta": {
                            "content": "",
                            "function_call": {"name": "read_file", "arguments": {"path": "a.py"}},
                            "functions_state_id": "st",
                        },
                        "index": 0,
                        "finish_reason": "function_call",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            },
        )
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    provider = _provider(handler)
    deltas = []

    async def on_delta(chunk):
        deltas.append(chunk)

    result = await provider.chat(
        ChatRequest(scenario="assistant", model="m", messages=[Message(role="user", content="hi")]), on_delta
    )
    assert deltas == ["Сейчас ", "посмотрю."]
    assert result.message.content == "Сейчас посмотрю."
    assert result.message.tool_calls[0].arguments == {"path": "a.py"}
    assert result.message.provider_state == {"functions_state_id": "st"}
    assert result.usage.prompt_tokens == 5


async def test_streaming_401_refreshes_token_once():
    tokens = iter(["old", "new"])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/oauth":
            return httpx.Response(200, json={"access_token": next(tokens), "expires_at": time.time() + 1800})
        if request.headers["Authorization"] == "Bearer old":
            return httpx.Response(401, json={"message": "token expired"})
        return httpx.Response(200, content=_sse({"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}]}))

    async def on_delta(chunk):
        pass

    result = await _provider(handler).chat(
        ChatRequest(scenario="x", model="m", messages=[Message(role="user", content="hi")]), on_delta
    )
    assert result.message.content == "ok"


def test_history_conversion_splits_parallel_calls_and_wraps_results():
    history = [
        Message(role="user", content="сделай"),
        Message(
            role="assistant",
            tool_calls=[ToolCall(id="c1", name="list_files"), ToolCall(id="c2", name="run_tests")],
        ),
        Message(role="tool", tool_call_id="c1", name="list_files", content="a.py"),
        Message(role="tool", tool_call_id="c2", name="run_tests", content='{"exit_code": 0}'),
        Message(
            role="assistant",
            tool_calls=[ToolCall(id="c3", name="read_file", arguments={"path": "a.py"})],
            provider_state={"functions_state_id": "s3"},
        ),
        Message(role="tool", tool_call_id="c3", name="read_file", content="print(1)"),
    ]
    out = to_gigachat_messages(history)
    assert [m["role"] for m in out] == ["user", "assistant", "function", "assistant", "function", "assistant", "function"]
    assert out[1]["function_call"]["name"] == "list_files"
    assert json.loads(out[2]["content"]) == {"result": "a.py"}
    assert json.loads(out[4]["content"]) == {"exit_code": 0}
    assert out[5]["functions_state_id"] == "s3"
