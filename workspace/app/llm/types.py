from enum import IntEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Priority(IntEnum):
    """Меньше — раньше. Кандидат ждёт ответа ассистента, оценку и генерацию можно подождать."""

    INTERACTIVE = 0
    GRADING = 1
    BACKGROUND = 2


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """Сообщение во внутреннем формате, близком к OpenAI; провайдеры переводят его в свой."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    # для role="tool": на какой вызов это ответ и имя функции
    tool_call_id: str | None = None
    name: str | None = None
    # непрозрачные данные провайдера, которые нужно вернуть в следующем запросе (например, functions_state_id GigaChat)
    provider_state: dict[str, Any] = Field(default_factory=dict)


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0


class ChatRequest(BaseModel):
    scenario: str
    model: str
    messages: list[Message]
    tools: list[ToolSpec] = Field(default_factory=list)
    temperature: float | None = None
    # Длинные ответы (генерация задачи целиком) упираются в лимит провайдера по умолчанию
    max_tokens: int | None = None
    # Только для заглушки: данные, по которым она изображает осмысленный ответ. Реальные провайдеры игнорируют.
    meta: dict[str, Any] = Field(default_factory=dict)


class ChatResult(BaseModel):
    message: Message
    usage: Usage = Field(default_factory=Usage)
    finish_reason: str = ""


class LLMError(Exception):
    """Ошибка, которую бессмысленно повторять: неверный запрос, отказ авторизации."""


class RateLimited(LLMError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ProviderUnavailable(LLMError):
    """Сеть, таймаут, 5xx — стоит повторить или уйти на запасной канал."""


class InvalidResponse(LLMError):
    """Модель ответила не по схеме."""
