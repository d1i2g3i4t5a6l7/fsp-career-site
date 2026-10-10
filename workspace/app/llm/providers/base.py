import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol

import httpx

from app.llm.types import ChatRequest, ChatResult, LLMError, ProviderUnavailable, RateLimited

# Получает очередной кусок текста ответа, пока модель его генерирует.
OnDelta = Callable[[str], Awaitable[None]]


class Provider(Protocol):
    async def chat(self, req: ChatRequest, on_delta: OnDelta | None = None) -> ChatResult:
        """Без on_delta — обычный запрос; с on_delta — потоковый, итог тот же ChatResult."""
        ...


async def iter_sse(resp: httpx.Response) -> AsyncIterator[dict[str, Any]]:
    """События server-sent events вида `data: {...}`, поток заканчивается `data: [DONE]`."""
    async for line in resp.aiter_lines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            return
        try:
            yield json.loads(data)
        except json.JSONDecodeError as exc:
            raise ProviderUnavailable(f"Битый кусок потока: {data[:200]}") from exc


def raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code < 400:
        return
    body = resp.text[:500]
    if resp.status_code == 429:
        raise RateLimited(f"429 from {resp.request.url.host}: {body}", _retry_after(resp))
    if resp.status_code >= 500:
        raise ProviderUnavailable(f"{resp.status_code} from {resp.request.url.host}: {body}")
    raise LLMError(f"{resp.status_code} from {resp.request.url.host}: {body}")


def _retry_after(resp: httpx.Response) -> float | None:
    value = resp.headers.get("retry-after")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_arguments(raw: Any) -> dict[str, Any]:
    """Аргументы вызова функции приходят то объектом, то JSON-строкой — в зависимости от API."""
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {"_raw": raw}
    return value if isinstance(value, dict) else {"_value": value}
