import json
import uuid
from typing import Any

import httpx

from app.llm.providers.base import OnDelta, iter_sse, parse_arguments, raise_for_status
from app.llm.types import ChatRequest, ChatResult, Message, ProviderUnavailable, ToolCall, Usage


class OpenAICompatProvider:
    """Любой OpenAI-совместимый /chat/completions: cloud.ru, vLLM, llama-server, Ollama."""

    def __init__(self, base_url: str, api_key: str = "", timeout: float = 120.0, client: httpx.AsyncClient | None = None):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def chat(self, req: ChatRequest, on_delta: OnDelta | None = None) -> ChatResult:
        body: dict[str, Any] = {
            "model": req.model,
            "messages": [_to_openai(m) for m in req.messages],
        }
        if req.tools:
            body["tools"] = [
                {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
                for t in req.tools
            ]
            body["tool_choice"] = "auto"
        if req.temperature is not None:
            body["temperature"] = req.temperature
        if req.max_tokens is not None:
            body["max_tokens"] = req.max_tokens
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}

        try:
            if on_delta is None:
                resp = await self._client.post(url, json=body, headers=headers)
                raise_for_status(resp)
                return _parse_response(resp.json())
            body |= {"stream": True, "stream_options": {"include_usage": True}}
            async with self._client.stream("POST", url, json=body, headers=headers) as resp:
                if resp.status_code >= 400:
                    await resp.aread()
                    raise_for_status(resp)
                return await _collect_stream(resp, on_delta)
        except httpx.TransportError as exc:
            raise ProviderUnavailable(f"{type(exc).__name__}: {exc}") from exc


def _parse_response(data: dict[str, Any]) -> ChatResult:
    choice = data["choices"][0]
    msg = choice.get("message") or {}
    tool_calls = [
        ToolCall(
            id=tc.get("id") or _new_id(),
            name=tc["function"]["name"],
            arguments=parse_arguments(tc["function"].get("arguments")),
        )
        for tc in msg.get("tool_calls") or []
    ]
    return _result(msg.get("content") or "", tool_calls, data.get("usage") or {}, choice.get("finish_reason") or "")


async def _collect_stream(resp: httpx.Response, on_delta: OnDelta) -> ChatResult:
    content: list[str] = []
    # Вызовы функций приходят кусками: имя и id в первом, аргументы — строкой по частям.
    calls: dict[int, dict[str, str]] = {}
    usage: dict[str, Any] = {}
    finish_reason = ""
    async for chunk in iter_sse(resp):
        usage = chunk.get("usage") or usage
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            if delta.get("content"):
                content.append(delta["content"])
                await on_delta(delta["content"])
            for tc in delta.get("tool_calls") or []:
                slot = calls.setdefault(tc.get("index", 0), {"id": "", "name": "", "arguments": ""})
                slot["id"] = tc.get("id") or slot["id"]
                fn = tc.get("function") or {}
                slot["name"] += fn.get("name") or ""
                slot["arguments"] += fn.get("arguments") or ""
            finish_reason = choice.get("finish_reason") or finish_reason
    tool_calls = [
        ToolCall(id=c["id"] or _new_id(), name=c["name"], arguments=parse_arguments(c["arguments"]))
        for _, c in sorted(calls.items())
    ]
    return _result("".join(content), tool_calls, usage, finish_reason)


def _result(content: str, tool_calls: list[ToolCall], usage: dict[str, Any], finish_reason: str) -> ChatResult:
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    return ChatResult(
        message=Message(role="assistant", content=content, tool_calls=tool_calls),
        usage=Usage(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            cached_tokens=cached or 0,
        ),
        finish_reason=finish_reason,
    )


def _new_id() -> str:
    return f"call_{uuid.uuid4().hex[:8]}"


def _to_openai(m: Message) -> dict[str, Any]:
    if m.role == "tool":
        return {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content}
    if m.role == "assistant" and m.tool_calls:
        return {
            "role": "assistant",
            "content": m.content or None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments, ensure_ascii=False)},
                }
                for tc in m.tool_calls
            ],
        }
    return {"role": m.role, "content": m.content}
