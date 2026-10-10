"""Харнесс ассистента: цикл «модель → инструмент → модель» над файлами попытки.

Ассистент читает файлы и запускает тесты сам, а правки только предлагает — применяет их кандидат.
Так в журнале видно, что кандидат принял, что отклонил и что поправил руками.
"""

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

from app.llm.gateway import Gateway
from app.llm.types import LLMError, Message, Priority, ToolCall, ToolSpec
from app.prompts import ASSISTANT_PROMPT_VERSION, FINAL_STEP_NOTE, assistant_system_prompt
from app.service import AttemptClosed, AttemptService, BadRequest, Conflict, NotFound, normalize_path

log = logging.getLogger(__name__)

_PATH = {"type": "string", "description": "Путь к файлу, например limiter.py"}

TOOLS = {
    "list_files": ToolSpec(
        name="list_files",
        description="Список файлов решения с числом строк.",
        parameters={"type": "object", "properties": {}},
    ),
    "read_file": ToolSpec(
        name="read_file",
        description="Прочитать актуальную версию файла решения.",
        parameters={"type": "object", "properties": {"path": _PATH}, "required": ["path"]},
    ),
    "propose_edit": ToolSpec(
        name="propose_edit",
        description=(
            "Предложить новую версию файла целиком. Правка не применяется сама: "
            "кандидат увидит дифф и примет или отклонит её."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": _PATH,
                "content": {"type": "string", "description": "Полное новое содержимое файла"},
                "summary": {"type": "string", "description": "Коротко: что меняется и зачем"},
            },
            "required": ["path", "content", "summary"],
        },
    ),
    "run_tests": ToolSpec(
        name="run_tests",
        description="Запустить тесты задачи в песочнице на текущей версии файлов (без непринятых правок).",
        parameters={"type": "object", "properties": {}},
    ),
}

# Сколько последних сообщений истории отправлять модели целиком; в более старых режем тяжёлое содержимое.
KEEP_RECENT = 12
MAX_HISTORY = 80

# Один и тот же вызов с теми же аргументами в одном ответе исполняется не больше двух раз;
# после двух заблокированных повторов модель обязана ответить текстом.
MAX_SAME_CALLS = 2
MAX_BLOCKED_REPEATS = 2
REPEAT_NOTE = (
    "Этот вызов с теми же аргументами уже был в этом ответе, результат не изменится. "
    "Не повторяй его — ответь кандидату или сделай другое действие."
)


class Busy(Exception):
    pass


class AssistantFailed(Exception):
    pass


class Assistant:
    def __init__(self, service: AttemptService, gateway: Gateway, max_steps: int = 25):
        self._service = service
        self._gateway = gateway
        self._max_steps = max_steps
        self._turn_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def reply(self, attempt_id: str, text: str) -> dict[str, Any]:
        text = text.strip()
        if not text:
            raise BadRequest("Пустое сообщение")
        lock = self._turn_locks[attempt_id]
        if lock.locked():
            raise Busy("Ассистент ещё отвечает на предыдущее сообщение")
        async with lock:
            self._status(attempt_id, "started")
            try:
                return await self._turn(attempt_id, text)
            finally:
                self._status(attempt_id, "idle")

    def _status(self, attempt_id: str, state: str, **extra: Any) -> None:
        """started → generating → tool → generating → … → idle"""
        self._service.notify(attempt_id, {"type": "assistant.status", "state": state, **extra})

    def _emit(self, attempt_id: str, chunk: str) -> None:
        self._service.notify(attempt_id, {"type": "assistant.delta", "text": chunk})

    async def _turn(self, attempt_id: str, text: str) -> dict[str, Any]:
        ctx = await self._service.begin_assistant_turn(attempt_id, text)
        history = [Message.model_validate(m) for m in ctx.history]
        if ctx.notes:
            text = "\n".join(f"[Событие: {n}]" for n in ctx.notes) + "\n\n" + text
        history.append(Message(role="user", content=text))
        # Если ход оборвётся посреди вызова инструмента, сохраняем историю до этой точки:
        # вызов без результата сломал бы следующий запрос к модели.
        safe_history = list(history)
        tools = [spec for name, spec in TOOLS.items() if name != "run_tests" or ctx.task.run]
        proposed: list[dict[str, Any]] = []
        # Текст каждого шага, который кандидат уже увидел. Модель может сказать «Сейчас посмотрю файл»
        # и вызвать инструмент — такой текст тоже часть ответа.
        parts: list[str] = []
        # Защита от зацикливания: на живом GigaChat ассистент 22 раза подряд звал run_tests.
        calls_seen: dict[str, int] = defaultdict(int)
        repeats_blocked = 0

        try:
            reply = None
            for step in range(self._max_steps + 1):
                files = await self._service.file_snapshot(attempt_id)
                messages = [
                    Message(
                        role="system",
                        content=assistant_system_prompt(ctx.task, sorted(files), ctx.category, ctx.level),
                    )
                ]
                messages += compact(history)
                final_step = step == self._max_steps or repeats_blocked >= MAX_BLOCKED_REPEATS
                if final_step:
                    messages.append(Message(role="user", content=FINAL_STEP_NOTE))
                step_text: list[str] = []

                async def on_delta(chunk: str) -> None:
                    if not step_text and any(parts):
                        self._emit(attempt_id, "\n\n")
                    step_text.append(chunk)
                    self._emit(attempt_id, chunk)

                result = await self._gateway.chat(
                    "assistant",
                    messages,
                    tools=tools,
                    priority=Priority.INTERACTIVE,
                    attempt_id=attempt_id,
                    prompt_version=ASSISTANT_PROMPT_VERSION,
                    meta={"files": sorted(files)},
                    on_delta=on_delta,
                    on_status=lambda status: self._status(attempt_id, **status),
                )
                msg = result.message
                if not step_text and msg.content.strip():
                    # провайдер ответил не потоком — показываем текст шага целиком
                    await on_delta(msg.content)
                parts.append("".join(step_text))
                if not msg.tool_calls or final_step:
                    reply = "\n\n".join(p.strip() for p in parts if p.strip())
                    if not reply:
                        reply = "Не получилось сформулировать ответ — уточните, пожалуйста, запрос."
                        self._emit(attempt_id, reply)
                    history.append(Message(role="assistant", content=msg.content.strip() or reply))
                    break
                step_messages = [msg]
                for call in msg.tool_calls:
                    key = f"{call.name}:{json.dumps(call.arguments, sort_keys=True, ensure_ascii=False)}"
                    calls_seen[key] += 1
                    if call.name != "propose_edit" and calls_seen[key] > MAX_SAME_CALLS:
                        repeats_blocked += 1
                        output = REPEAT_NOTE
                    else:
                        output = await self._run_tool(attempt_id, call, proposed)
                    step_messages.append(Message(role="tool", tool_call_id=call.id, name=call.name, content=output))
                history += step_messages
                safe_history = list(history)
        except LLMError as exc:
            log.warning("assistant failed for attempt %s: %s", attempt_id, exc)
            await self._service.finish_assistant_turn(
                attempt_id, _dump(safe_history), error="Ассистент сейчас недоступен, попробуйте ещё раз."
            )
            raise AssistantFailed(str(exc)) from exc
        except AttemptClosed as exc:
            await self._service.finish_assistant_turn(attempt_id, _dump(safe_history), error=str(exc))
            raise

        edit_ids = [e["id"] for e in proposed]
        await self._service.finish_assistant_turn(attempt_id, _dump(history), reply=reply, edit_ids=edit_ids)
        return {"reply": reply, "edits": proposed}

    async def _run_tool(self, attempt_id: str, call: ToolCall, proposed: list[dict[str, Any]]) -> str:
        args = call.arguments
        self._status(attempt_id, "tool", tool=call.name, **({"path": str(args["path"])} if "path" in args else {}))
        try:
            if call.name == "list_files":
                files = await self._service.file_snapshot(attempt_id)
                output = "\n".join(f"{p} — {c.count(chr(10)) + 1} строк" for p, c in sorted(files.items())) or "Файлов нет"
            elif call.name == "read_file":
                files = await self._service.file_snapshot(attempt_id)
                path = normalize_path(args.get("path", ""))
                output = files[path] if path in files else f"Файла {path} нет. Есть: {', '.join(sorted(files))}"
            elif call.name == "propose_edit":
                edit = await self._service.propose_edit(
                    attempt_id, args.get("path", ""), str(args.get("content", "")), str(args.get("summary", ""))
                )
                proposed.append(edit)
                # Событие edit.proposed уже в журнале — отдельный assistant.tool не пишем.
                return (
                    f"Правка #{edit['id']} в {edit['path']} (+{edit['added']} −{edit['removed']} строк) "
                    "показана кандидату и ждёт его решения. Не считай её применённой."
                )
            elif call.name == "run_tests":
                return (await self._service.run_tests(attempt_id, by="assistant")).summary(3000)
            else:
                output = f"Неизвестный инструмент {call.name}"
        except (BadRequest, NotFound, Conflict) as exc:
            output = f"Ошибка: {exc}"
        except AttemptClosed:
            raise
        await self._service.log_tool(attempt_id, call.name, _loggable_args(call), output[:500])
        return output


def compact(history: list[Message]) -> list[Message]:
    """Старые результаты инструментов и тела правок урезаем: модели нужна суть, а не копии файлов."""
    if len(history) > MAX_HISTORY:
        start = len(history) - MAX_HISTORY
        # режем только по границе сообщения кандидата, чтобы не оторвать результат инструмента от вызова
        while start < len(history) and history[start].role != "user":
            start += 1
        history = history[start:]
    cut = len(history) - KEEP_RECENT
    out = []
    for i, m in enumerate(history):
        if i < cut and m.role == "tool" and len(m.content) > 300:
            m = m.model_copy(update={"content": m.content[:300] + "\n…[сокращено]"})
        elif i < cut and m.role == "assistant" and any(tc.name == "propose_edit" for tc in m.tool_calls):
            calls = [
                tc.model_copy(update={"arguments": {**tc.arguments, "content": "[содержимое правки опущено]"}})
                if tc.name == "propose_edit"
                else tc
                for tc in m.tool_calls
            ]
            m = m.model_copy(update={"tool_calls": calls})
        out.append(m)
    return out


def _dump(history: list[Message]) -> list[dict[str, Any]]:
    return [m.model_dump(exclude_defaults=True) for m in history]


def _loggable_args(call: ToolCall) -> dict[str, Any]:
    return {k: v for k, v in call.arguments.items() if k != "content"}
