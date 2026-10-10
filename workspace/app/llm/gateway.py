"""Единственная точка обращения к моделям.

Сценарий (ассистент, «заказчик», оценщик…) → канал → модель. На каждом канале свой
лимит одновременных запросов и очередь с приоритетами (ChannelLimiter). Здесь же
повторы при 429 и сбоях, переход на запасной канал и журнал вызовов.
"""

import asyncio
import json
import logging
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.balancer import ChannelLimiter
from app.llm.providers.base import OnDelta, Provider
from app.llm.types import (
    ChatRequest,
    ChatResult,
    InvalidResponse,
    LLMError,
    Message,
    Priority,
    ProviderUnavailable,
    RateLimited,
    ToolSpec,
)

log = logging.getLogger(__name__)

M = TypeVar("M", bound=BaseModel)
Journal = Callable[[dict[str, Any]], Awaitable[None]]
# Статус запроса для интерфейса: {"state": "generating"} — модель начала работать над запросом
OnStatus = Callable[[dict[str, Any]], None]


@dataclass
class Channel:
    name: str
    provider: Provider
    model: str
    limiter: ChannelLimiter


class _Stream:
    """Передаёт куски ответа дальше и помнит, видел ли их уже кандидат.
    Если видел — повторять запрос или уходить на запасной канал нельзя: текст задвоится."""

    def __init__(self, on_delta: OnDelta):
        self._on_delta = on_delta
        self.emitted = False

    async def __call__(self, chunk: str) -> None:
        self.emitted = True
        await self._on_delta(chunk)


class Gateway:
    def __init__(
        self,
        channels: dict[str, Channel],
        routes: dict[str, str],
        fallback: str | None = None,
        *,
        max_retries: int = 3,
        journal: Journal | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self.channels = channels
        self._routes = routes
        self._fallback = fallback
        self._max_retries = max_retries
        self._journal = journal
        self._sleep = sleep

    def resolve(self, scenario: str) -> Channel:
        name = self._routes.get(scenario, self._fallback)
        if name in self.channels:
            return self.channels[name]
        if self._fallback in self.channels:
            return self.channels[self._fallback]
        raise LLMError(f"Нет настроенного канала для сценария «{scenario}»")

    async def chat(
        self,
        scenario: str,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        priority: Priority = Priority.INTERACTIVE,
        temperature: float | None = None,
        max_tokens: int | None = None,
        attempt_id: str | None = None,
        prompt_version: str = "",
        meta: dict[str, Any] | None = None,
        on_delta: OnDelta | None = None,
        on_status: OnStatus | None = None,
    ) -> ChatResult:
        """С on_delta ответ генерируется потоком: куски текста приходят в on_delta по мере генерации."""
        channel = self.resolve(scenario)
        stream = _Stream(on_delta) if on_delta else None
        call = dict(
            scenario=scenario,
            messages=messages,
            tools=tools or [],
            priority=priority,
            temperature=temperature,
            max_tokens=max_tokens,
            attempt_id=attempt_id,
            prompt_version=prompt_version,
            meta=meta or {},
            stream=stream,
            on_status=on_status,
        )
        try:
            return await self._call_with_retries(channel, **call)
        except ProviderUnavailable:
            backup = self.channels.get(self._fallback or "")
            if backup is None or backup is channel or (stream and stream.emitted):
                raise
            log.warning("channel %s unavailable, falling back to %s", channel.name, backup.name)
            return await self._call_with_retries(backup, **call)

    async def chat_json(
        self,
        scenario: str,
        messages: list[Message],
        schema: type[M],
        *,
        priority: Priority = Priority.INTERACTIVE,
        attempt_id: str | None = None,
        prompt_version: str = "",
        meta: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        fix_attempts: int = 2,
    ) -> M:
        """Ответ строго по pydantic-схеме: схема дописывается в системный промпт, ответ валидируется,
        при ошибке модели показывают её ошибку и просят исправить."""
        instruction = (
            "Ответь только JSON-объектом, без пояснений и без markdown, по JSON-схеме:\n"
            + json.dumps(schema.model_json_schema(), ensure_ascii=False)
        )
        msgs = _append_to_system(messages, instruction)
        for i in range(fix_attempts + 1):
            result = await self.chat(
                scenario,
                msgs,
                priority=priority,
                attempt_id=attempt_id,
                prompt_version=prompt_version,
                meta=meta,
                max_tokens=max_tokens,
            )
            text = result.message.content
            try:
                return schema.model_validate_json(extract_json(text))
            except (ValidationError, ValueError) as exc:
                if i == fix_attempts:
                    raise InvalidResponse(f"Ответ не по схеме {schema.__name__}: {exc}") from exc
                msgs = msgs + [
                    Message(role="assistant", content=text),
                    Message(role="user", content=f"Ответ не прошёл проверку схемы: {exc}. Пришли исправленный JSON."),
                ]
        raise AssertionError("unreachable")

    async def _call_with_retries(self, channel: Channel, **call: Any) -> ChatResult:
        req = ChatRequest(
            scenario=call["scenario"],
            model=channel.model,
            messages=call["messages"],
            tools=call["tools"],
            temperature=call["temperature"],
            max_tokens=call["max_tokens"],
            meta=call["meta"],
        )
        stream: _Stream | None = call["stream"]
        on_status: OnStatus | None = call["on_status"]

        for attempt in range(self._max_retries + 1):
            retry_delay = 0.0
            queued_at = time.monotonic()
            async with channel.limiter.slot(call["priority"]):
                if on_status:
                    on_status({"state": "generating"})
                started_at = time.monotonic()
                timing = {"queue_ms": _ms(started_at - queued_at)}
                try:
                    result = await channel.provider.chat(req, stream)
                except RateLimited as exc:
                    # Пауза на весь канал: остальные запросы из очереди тоже подождут.
                    channel.limiter.pause(exc.retry_after or _backoff(attempt))
                    await self._record(channel, call, "rate_limited", started_at, timing, error=str(exc))
                    if attempt == self._max_retries or (stream and stream.emitted):
                        raise
                    continue
                except ProviderUnavailable as exc:
                    await self._record(channel, call, "unavailable", started_at, timing, error=str(exc))
                    if attempt == self._max_retries or (stream and stream.emitted):
                        raise
                    retry_delay = _backoff(attempt)
                except LLMError as exc:
                    await self._record(channel, call, "error", started_at, timing, error=str(exc))
                    raise
                else:
                    await self._record(channel, call, "ok", started_at, timing, result=result)
                    return result
            # Ждём вне слота, чтобы не держать канал занятым.
            await self._sleep(retry_delay)
        raise AssertionError("unreachable")

    async def _record(
        self,
        channel: Channel,
        call: dict[str, Any],
        status: str,
        started_at: float,
        timing: dict[str, int],
        *,
        result: ChatResult | None = None,
        error: str = "",
    ) -> None:
        if self._journal is None:
            return
        usage = result.usage if result else None
        entry = {
            "scenario": call["scenario"],
            "channel": channel.name,
            "model": channel.model,
            "prompt_version": call["prompt_version"],
            "attempt_id": call["attempt_id"],
            "status": status,
            "error": error[:2000],
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "cached_tokens": usage.cached_tokens if usage else 0,
            "queue_ms": timing["queue_ms"],
            "duration_ms": _ms(time.monotonic() - started_at),
            "request": [m.model_dump(exclude_defaults=True) for m in call["messages"]],
            "response": result.message.model_dump(exclude_defaults=True) if result else None,
        }
        try:
            await self._journal(entry)
        except Exception:  # журнал не должен ронять ответ кандидату
            log.exception("failed to write LLM call journal")


def _backoff(attempt: int) -> float:
    return float(min(2**attempt, 30))


def _ms(seconds: float) -> int:
    return int(seconds * 1000)


def _append_to_system(messages: list[Message], text: str) -> list[Message]:
    if messages and messages[0].role == "system":
        first = messages[0].model_copy(update={"content": messages[0].content + "\n\n" + text})
        return [first, *messages[1:]]
    return [Message(role="system", content=text), *messages]


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def extract_json(text: str) -> str:
    text = _FENCE.sub("", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("в ответе нет JSON-объекта")
    return text[start : end + 1]
