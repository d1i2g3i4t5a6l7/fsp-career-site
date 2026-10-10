"""API Сбера (GigaChat): https://developers.sber.ru/docs/ru/gigachat/api/

Отличия от OpenAI, которые здесь закрываются:
- ключ авторизации меняется на токен на 30 минут (OAuth, заголовок RqUID);
- вместо tools — functions, за раз модель вызывает одну функцию;
- результат функции — сообщение с ролью function, content обязан быть JSON-объектом;
- functions_state_id из ответа нужно вернуть в том же assistant-сообщении в следующем запросе;
- сертификаты НУЦ Минцифры.
"""

import asyncio
import json
import ssl
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.llm.providers.base import OnDelta, iter_sse, parse_arguments, raise_for_status
from app.llm.types import ChatRequest, ChatResult, LLMError, Message, ProviderUnavailable, ToolCall, Usage

_TOKEN_REFRESH_MARGIN_S = 60
# Цепочка НУЦ Минцифры (Russian Trusted Root CA до 2032 + Sub CA до 06.03.2027) лежит в репозитории:
# без неё сертификат Сбера не проверить. Источник — https://www.gosuslugi.ru/crt
_RUSSIAN_TRUSTED_CA = Path(__file__).resolve().parents[3] / "certs" / "russian_trusted_ca.pem"


class GigaChatProvider:
    def __init__(
        self,
        auth_key: str,
        *,
        scope: str = "GIGACHAT_API_PERS",
        auth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        base_url: str = "https://api.giga.chat/v1",
        ca_bundle: str = "",
        verify_ssl: bool = True,
        timeout: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ):
        self._auth_key = auth_key
        self._scope = scope
        self._auth_url = auth_url
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout, verify=_ssl_context(ca_bundle, verify_ssl))
        self._token = ""
        self._token_expires_at = 0.0
        self._token_lock = asyncio.Lock()

    async def chat(self, req: ChatRequest, on_delta: OnDelta | None = None) -> ChatResult:
        body: dict[str, Any] = {"model": req.model, "messages": to_gigachat_messages(req.messages)}
        if req.tools:
            body["functions"] = [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in req.tools]
            body["function_call"] = "auto"
        if req.temperature is not None:
            body["temperature"] = req.temperature
        if req.max_tokens is not None:
            body["max_tokens"] = req.max_tokens

        result = await self._send(body, on_delta)
        if result is None:
            # 401: токен мог протухнуть раньше срока — берём новый и повторяем один раз
            self._token = ""
            result = await self._send(body, on_delta)
            if result is None:
                raise LLMError("GigaChat отклонил свежий токен (401)")
        return result

    async def _send(self, body: dict[str, Any], on_delta: OnDelta | None) -> ChatResult | None:
        """None — сервер ответил 401 до начала ответа."""
        token = await self._get_token()
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        try:
            if on_delta is None:
                resp = await self._client.post(url, json=body, headers=headers)
                if resp.status_code == 401:
                    return None
                raise_for_status(resp)
                return parse_gigachat_response(resp.json())
            async with self._client.stream("POST", url, json={**body, "stream": True}, headers=headers) as resp:
                if resp.status_code == 401:
                    return None
                if resp.status_code >= 400:
                    await resp.aread()
                    raise_for_status(resp)
                return await _collect_stream(resp, on_delta)
        except httpx.TransportError as exc:
            raise ProviderUnavailable(f"{type(exc).__name__}: {exc}") from exc

    async def _get_token(self) -> str:
        async with self._token_lock:
            if self._token and time.time() < self._token_expires_at - _TOKEN_REFRESH_MARGIN_S:
                return self._token
            try:
                resp = await self._client.post(
                    self._auth_url,
                    data={"scope": self._scope},
                    headers={
                        "Authorization": f"Basic {self._auth_key}",
                        "RqUID": str(uuid.uuid4()),
                        "Accept": "application/json",
                    },
                )
            except httpx.TransportError as exc:
                raise ProviderUnavailable(f"OAuth {type(exc).__name__}: {exc}") from exc
            if resp.status_code in (400, 401, 403):
                raise LLMError(f"GigaChat OAuth отклонил ключ ({resp.status_code}): {resp.text[:300]}")
            raise_for_status(resp)
            data = resp.json()
            expires_at = float(data["expires_at"])
            # В схеме — миллисекунды, в части примеров — секунды.
            if expires_at > 1e12:
                expires_at /= 1000
            self._token = data["access_token"]
            self._token_expires_at = expires_at
            return self._token


def _ssl_context(ca_bundle: str, verify_ssl: bool) -> ssl.SSLContext | bool:
    if not verify_ssl:
        return False
    ctx = ssl.create_default_context()
    if _RUSSIAN_TRUSTED_CA.is_file():
        ctx.load_verify_locations(cafile=_RUSSIAN_TRUSTED_CA)
    if ca_bundle:
        ctx.load_verify_locations(cafile=ca_bundle)
    return ctx


def to_gigachat_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """GigaChat принимает один вызов функции на assistant-сообщение, и сразу за ним должен идти результат.
    Если история пришла от модели с параллельными вызовами, раскладываем их в цепочку пар «вызов → результат»."""
    results = {m.tool_call_id: m for m in messages if m.role == "tool"}
    consumed: set[str] = set()
    out: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "tool":
            if m.tool_call_id not in consumed:
                out.append(_function_result(m))
            continue
        if m.role == "assistant" and m.tool_calls:
            for i, call in enumerate(m.tool_calls):
                msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": m.content if i == 0 else "",
                    "function_call": {"name": call.name, "arguments": call.arguments},
                }
                state_id = m.provider_state.get("functions_state_id")
                if state_id and len(m.tool_calls) == 1:
                    msg["functions_state_id"] = state_id
                out.append(msg)
                result = results.get(call.id)
                if result is not None:
                    out.append(_function_result(result))
                    consumed.add(call.id)
            continue
        out.append({"role": m.role, "content": m.content})
    return out


def _function_result(m: Message) -> dict[str, Any]:
    content = m.content
    try:
        is_object = isinstance(json.loads(content), dict)
    except (TypeError, json.JSONDecodeError):
        is_object = False
    if not is_object:
        content = json.dumps({"result": content}, ensure_ascii=False)
    return {"role": "function", "name": m.name or "", "content": content}


async def _collect_stream(resp: httpx.Response, on_delta: OnDelta) -> ChatResult:
    """Текст приходит кусками; вызов функции — целиком одним куском вместе с functions_state_id."""
    content: list[str] = []
    message: dict[str, Any] = {}
    usage: dict[str, Any] = {}
    finish_reason = ""
    async for chunk in iter_sse(resp):
        usage = chunk.get("usage") or usage
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            if delta.get("content"):
                content.append(delta["content"])
                await on_delta(delta["content"])
            for key in ("function_call", "functions_state_id"):
                if delta.get(key):
                    message[key] = delta[key]
            finish_reason = choice.get("finish_reason") or finish_reason
    message["content"] = "".join(content)
    return parse_gigachat_response({"choices": [{"message": message, "finish_reason": finish_reason}], "usage": usage})


def parse_gigachat_response(data: dict[str, Any]) -> ChatResult:
    choice = data["choices"][0]
    finish_reason = choice.get("finish_reason") or ""
    if finish_reason == "error":
        # Так GigaChat сообщает, что модель сгенерировала некорректные аргументы функции; повтор обычно помогает.
        raise ProviderUnavailable("GigaChat вернул finish_reason=error (некорректный вызов функции)")
    msg = choice.get("message") or {}
    tool_calls = []
    if msg.get("function_call"):
        fc = msg["function_call"]
        tool_calls.append(
            ToolCall(id=f"call_{uuid.uuid4().hex[:8]}", name=fc["name"], arguments=parse_arguments(fc.get("arguments")))
        )
    state = {"functions_state_id": msg["functions_state_id"]} if msg.get("functions_state_id") else {}
    usage = data.get("usage") or {}
    return ChatResult(
        message=Message(role="assistant", content=msg.get("content") or "", tool_calls=tool_calls, provider_state=state),
        usage=Usage(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            cached_tokens=usage.get("precached_prompt_tokens", 0),
        ),
        finish_reason=finish_reason,
    )
