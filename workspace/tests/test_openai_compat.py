import json

import httpx

from app.llm.providers.openai_compat import OpenAICompatProvider
from app.llm.types import ChatRequest, Message, ToolCall, ToolSpec


def _sse(*chunks) -> bytes:
    return ("".join(f"data: {json.dumps(c, ensure_ascii=False)}\n\n" for c in chunks) + "data: [DONE]\n\n").encode()


def _provider(handler) -> OpenAICompatProvider:
    return OpenAICompatProvider("https://llm.test/v1", "key", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


REQ = ChatRequest(
    scenario="assistant",
    model="m",
    messages=[
        Message(role="user", content="почини"),
        Message(role="assistant", tool_calls=[ToolCall(id="c0", name="list_files")]),
        Message(role="tool", tool_call_id="c0", name="list_files", content="a.py"),
    ],
    tools=[ToolSpec(name="read_file", description="d", parameters={"type": "object", "properties": {}})],
)


async def test_streaming_assembles_tool_call_arguments_from_fragments():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer key"
        assert body["stream"] is True and body["tools"][0]["function"]["name"] == "read_file"
        # история с вызовом инструмента ушла в формате OpenAI
        assert body["messages"][1]["tool_calls"][0]["function"]["arguments"] == "{}"
        assert body["messages"][2] == {"role": "tool", "tool_call_id": "c0", "content": "a.py"}
        return httpx.Response(
            200,
            content=_sse(
                {"choices": [{"index": 0, "delta": {"content": "Смотрю "}}]},
                {"choices": [{"index": 0, "delta": {"content": "файл."}}]},
                {
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "tool_calls": [
                                    {"index": 0, "id": "call_1", "type": "function", "function": {"name": "read_file", "arguments": '{"pa'}}
                                ]
                            },
                        }
                    ]
                },
                {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": 'th": "a.py"}'}}]}}]},
                {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
                {"choices": [], "usage": {"prompt_tokens": 7, "completion_tokens": 4}},
            ),
        )

    deltas = []

    async def on_delta(chunk):
        deltas.append(chunk)

    result = await _provider(handler).chat(REQ, on_delta)
    assert deltas == ["Смотрю ", "файл."]
    [call] = result.message.tool_calls
    assert (call.id, call.name, call.arguments) == ("call_1", "read_file", {"path": "a.py"})
    assert result.finish_reason == "tool_calls" and result.usage.completion_tokens == 4


async def test_non_streaming_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "stream" not in json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [{"id": "x", "function": {"name": "read_file", "arguments": '{"path": "b.py"}'}}],
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            },
        )

    result = await _provider(handler).chat(REQ)
    assert result.message.content == "" and result.message.tool_calls[0].arguments == {"path": "b.py"}
