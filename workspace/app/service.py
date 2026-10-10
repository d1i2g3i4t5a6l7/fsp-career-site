"""Сессия решения задачи: файлы, правки ассистента, запуски тестов, журнал событий.

Каждое действие пишет событие в журнал (SessionEvent) и рассылает его открытым WebSocket.
Изменения одной попытки идут под её замком, чтобы правки и сохранения файлов не затирали друг друга.
"""

import asyncio
import difflib
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bus import EventBus
from app.db import utcnow
from app.models import Attempt, FileEdit, Grading, SessionEvent, TaskRow
from app.sandbox import RunResult, Runner
from app.tasks import Task, TaskReview, task_view

MAX_FILES = 50
MAX_FILE_CHARS = 200_000


class NotFound(Exception):
    pass


class AttemptClosed(Exception):
    pass


class Conflict(Exception):
    pass


class BadRequest(Exception):
    pass


@dataclass
class AssistantContext:
    task: Task
    history: list[dict[str, Any]]
    notes: list[str]
    category: str
    level: str


def normalize_path(path: str) -> str:
    raw = str(path).strip().replace("\\", "/")
    parts = [p for p in raw.split("/") if p not in ("", ".")]
    if not parts or raw.startswith("/") or ".." in parts or ":" in parts[0] or len(raw) > 200:
        raise BadRequest(f"Недопустимый путь: {path!r}")
    return "/".join(parts)


def make_diff(path: str, before: str | None, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            _lines(before or ""),
            _lines(after),
            fromfile="/dev/null" if before is None else f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def diff_stats(diff: str) -> tuple[int, int]:
    lines = diff.splitlines()
    added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
    return added, removed


def _lines(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    return lines


def _iso(value) -> str | None:
    return value.isoformat() + "Z" if value else None


def event_view(ev: SessionEvent) -> dict[str, Any]:
    return {"id": ev.id, "type": ev.type, "payload": ev.payload, "at": _iso(ev.created_at)}


def edit_view(edit: FileEdit) -> dict[str, Any]:
    diff = make_diff(edit.path, edit.base_content, edit.new_content)
    added, removed = diff_stats(diff)
    return {
        "id": edit.id,
        "path": edit.path,
        "summary": edit.summary,
        "status": edit.status,
        "reason": edit.reason,
        "diff": diff,
        "added": added,
        "removed": removed,
        "is_new_file": edit.base_content is None,
        "created_at": _iso(edit.created_at),
    }


def stats_from_events(events: list[SessionEvent]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for ev in events:
        counts[ev.type] += 1
    return {
        # «Сколько итераций понадобилось» — число обращений к ассистенту
        "assistant_requests": counts["assistant.user_message"],
        "manual_edits": counts["file.saved"],
        "edits_proposed": counts["edit.proposed"],
        "edits_accepted": counts["edit.accepted"],
        "edits_rejected": counts["edit.rejected"],
        "test_runs": counts["tests.run"],
        # Уход со вкладки во время теста запрещён: любой уход — нарушение, решает человек
        "tab_leaves": counts["tab.left"],
    }


TAB_EVENTS = ("tab.left", "tab.back")


def tab_violations(events: list[SessionEvent], ended_at: datetime) -> dict[str, int]:
    """Уходы со вкладки: сколько раз и сколько секунд всего. Не вернулся до конца теста — считаем до конца."""
    count, away, left_at = 0, 0.0, None
    for ev in events:
        if ev.type == "tab.left":
            count += 1
            left_at = ev.created_at
        elif ev.type == "tab.back" and left_at is not None:
            away += (ev.created_at - left_at).total_seconds()
            left_at = None
    if left_at is not None and ended_at > left_at:
        away += (ended_at - left_at).total_seconds()
    return {"count": count, "away_s": int(away)}


def chat_from_events(events: list[SessionEvent]) -> list[dict[str, Any]]:
    """Лента чата для перерисовки после перезагрузки страницы."""
    chat = []
    for ev in events:
        if ev.type == "assistant.user_message":
            chat.append({"role": "user", "text": ev.payload["text"], "at": _iso(ev.created_at)})
        elif ev.type == "assistant.message":
            chat.append(
                {
                    "role": "assistant",
                    "text": ev.payload["text"],
                    "edit_ids": ev.payload.get("edit_ids", []),
                    "at": _iso(ev.created_at),
                }
            )
        elif ev.type == "assistant.error":
            chat.append({"role": "error", "text": ev.payload["error"], "at": _iso(ev.created_at)})
    return chat


class AttemptService:
    def __init__(self, sessions: async_sessionmaker, runner: Runner, bus: EventBus):
        self._sessions = sessions
        self._runner = runner
        self._bus = bus
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    # --- жизненный цикл попытки ---

    async def list_tasks(
        self, category: str | None = None, grade: str | None = None, status: str | None = None
    ) -> list[Task]:
        async with self._sessions() as s:
            rows = (await s.scalars(select(TaskRow).order_by(TaskRow.created_at.desc()))).all()
        tasks = [Task.model_validate(r.data) for r in rows]
        return [
            t
            for t in tasks
            if (category is None or t.has_category(category))
            and (grade is None or grade in t.grades)
            and (status is None or t.status == status)
        ]

    async def review_task(self, task_id: str, expert: str, approved: bool, comment: str) -> Task:
        """Эксперт проверил задачу на решаемость: одобренная выдаётся кандидатам, отклонённая — нет.
        Решение можно поменять, например снять уже опубликованную задачу."""
        async with self._sessions() as s:
            row = await s.get(TaskRow, task_id)
            if row is None:
                raise NotFound(f"Задача {task_id} не найдена")
            task = Task.model_validate(row.data)
            task.status = "published" if approved else "rejected"
            task.review = TaskReview(expert=expert, approved=approved, comment=comment, at=_iso(utcnow()))
            row.data = task.model_dump()
            await s.commit()
        return task

    async def get_task(self, task_id: str) -> Task:
        async with self._sessions() as s:
            row = await s.get(TaskRow, task_id)
        if row is None:
            raise NotFound(f"Задача {task_id} не найдена")
        return Task.model_validate(row.data)

    async def pick_task(self, candidate_id: str, category: str, level: str) -> str:
        """Случайная одобренная экспертом задача с этой категорией и грейдом — сначала из тех, что кандидат ещё не решал."""
        matching = [t.id for t in await self.list_tasks(category, level, status="published")]
        if not matching:
            raise NotFound(f"Нет задач для {category} · {level}")
        async with self._sessions() as s:
            solved = set((await s.scalars(select(Attempt.task_id).where(Attempt.candidate_id == candidate_id))).all())
        fresh = [tid for tid in matching if tid not in solved]
        return random.choice(fresh or matching)

    async def start(self, task_id: str, candidate_id: str, category: str, level: str) -> str:
        async with self._sessions() as s:
            row = await s.get(TaskRow, task_id)
            if row is None:
                raise NotFound(f"Задача {task_id} не найдена")
            task = Task.model_validate(row.data)
            # Задачу на проверке можно открыть по id — так эксперт прорешивает её сам
            if task.status == "rejected":
                raise Conflict(f"Задача {task.id} отклонена экспертом")
            if not task.has_category(category) or level not in task.grades:
                raise BadRequest(f"Задача {task.id} не для {category} · {level}: {task.categories} · {task.grades}")
            # Категорию пишем так, как она записана в задаче, чтобы грейды не дробились по регистру
            category = next(c for c in task.categories if c.lower() == category.strip().lower())
            now = utcnow()
            attempt = Attempt(
                task_id=task.id,
                candidate_id=candidate_id,
                category=category,
                level=level,
                started_at=now,
                deadline_at=now + timedelta(minutes=task.time_limit_min),
                task=task.model_dump(),
                files=dict(task.files),
                assistant_history=[],
                notes=[],
            )
            s.add(attempt)
            await s.flush()
            ev = self._event(
                s,
                attempt.id,
                "attempt.started",
                {"task_id": task.id, "candidate_id": candidate_id, "category": category, "level": level},
            )
            await s.commit()
        self._publish(ev)
        return attempt.id

    async def state(self, attempt_id: str) -> dict[str, Any]:
        async with self._sessions() as s:
            attempt = await self._get(s, attempt_id)
            expired = await self._expire_if_due(s, attempt)
            edits = (await s.scalars(select(FileEdit).where(FileEdit.attempt_id == attempt_id).order_by(FileEdit.id))).all()
            events = (
                await s.scalars(select(SessionEvent).where(SessionEvent.attempt_id == attempt_id).order_by(SessionEvent.id))
            ).all()
            grading = await s.get(Grading, attempt_id)
        if expired:
            self._publish(expired)
        remaining = (attempt.deadline_at - utcnow()).total_seconds() if attempt.status == "active" else 0
        if grading is not None:
            grading_status = grading.status
        else:
            grading_status = "not_submitted" if attempt.status == "active" else "pending"
        return {
            "id": attempt.id,
            "candidate_id": attempt.candidate_id,
            # «Backend · Senior» — на что проходит тест
            "category": attempt.category,
            "level": attempt.level,
            "status": attempt.status,
            # not_submitted → pending → running → done | failed; результат — GET /attempts/{id}/result
            "grading_status": grading_status,
            "started_at": _iso(attempt.started_at),
            "deadline_at": _iso(attempt.deadline_at),
            "submitted_at": _iso(attempt.submitted_at),
            "remaining_s": max(0, int(remaining)),
            "task": task_view(Task.model_validate(attempt.task)).model_dump(),
            "files": attempt.files,
            "edits": [edit_view(e) for e in edits],
            "stats": stats_from_events(list(events)),
            "chat": chat_from_events(list(events)),
        }

    async def ensure_exists(self, attempt_id: str) -> None:
        async with self._sessions() as s:
            await self._get(s, attempt_id)

    async def events(self, attempt_id: str, after_id: int = 0) -> list[dict[str, Any]]:
        async with self._sessions() as s:
            await self._get(s, attempt_id)
            rows = (
                await s.scalars(
                    select(SessionEvent)
                    .where(SessionEvent.attempt_id == attempt_id, SessionEvent.id > after_id)
                    .order_by(SessionEvent.id)
                )
            ).all()
        return [event_view(e) for e in rows]

    async def expire_overdue(self) -> list[str]:
        """Закрыть попытки, у которых вышло время, — даже если кандидат больше ничего не нажимал."""
        async with self._sessions() as s:
            overdue = (
                await s.scalars(select(Attempt.id).where(Attempt.status == "active", Attempt.deadline_at < utcnow()))
            ).all()
        expired = []
        for attempt_id in overdue:
            async with self._locks[attempt_id], self._sessions() as s:
                ev = await self._expire_if_due(s, await self._get(s, attempt_id))
            if ev:
                self._publish(ev)
                expired.append(attempt_id)
        return expired

    async def submit(self, attempt_id: str) -> dict[str, Any]:
        async with self._locks[attempt_id], self._sessions() as s:
            attempt = await self._active(s, attempt_id)
            attempt.status = "submitted"
            attempt.submitted_at = utcnow()
            ev = self._event(s, attempt_id, "attempt.submitted", {"files": sorted(attempt.files)})
            await s.commit()
        self._publish(ev)
        return {"status": attempt.status, "submitted_at": _iso(attempt.submitted_at)}

    async def record_focus(self, attempt_id: str, left: bool) -> dict[str, Any]:
        """Кандидат ушёл со вкладки теста или вернулся. Повтор того же состояния не пишем."""
        type_ = "tab.left" if left else "tab.back"
        async with self._locks[attempt_id], self._sessions() as s:
            await self._active(s, attempt_id)
            last = await s.scalar(
                select(SessionEvent.type)
                .where(SessionEvent.attempt_id == attempt_id, SessionEvent.type.in_(TAB_EVENTS))
                .order_by(SessionEvent.id.desc())
                .limit(1)
            )
            if last == type_ or (last is None and not left):
                return {"recorded": False}
            ev = self._event(s, attempt_id, type_, {})
            await s.commit()
        self._publish(ev)
        return {"recorded": True}

    # --- файлы и правки ---

    async def save_file(self, attempt_id: str, path: str, content: str) -> dict[str, Any]:
        """Ручная правка кандидата в редакторе."""
        path = normalize_path(path)
        _check_size(content)
        published = []
        async with self._locks[attempt_id], self._sessions() as s:
            attempt = await self._active(s, attempt_id)
            before = attempt.files.get(path)
            if before == content:
                return {"changed": False}
            if before is None and len(attempt.files) >= MAX_FILES:
                raise BadRequest(f"Не больше {MAX_FILES} файлов")
            attempt.files = {**attempt.files, path: content}
            _add_note(attempt, f"кандидат вручную изменил файл {path}")
            published.append(self._event(s, attempt_id, "file.saved", {"path": path, "diff": make_diff(path, before, content)}))
            published += await self._mark_stale(s, attempt_id, path)
            await s.commit()
        for ev in published:
            self._publish(ev)
        return {"changed": True}

    async def propose_edit(self, attempt_id: str, path: str, content: str, summary: str) -> dict[str, Any]:
        path = normalize_path(path)
        _check_size(content)
        async with self._locks[attempt_id], self._sessions() as s:
            attempt = await self._active(s, attempt_id)
            base = attempt.files.get(path)
            if base == content:
                raise BadRequest(f"Правка не меняет файл {path}")
            edit = FileEdit(attempt_id=attempt_id, path=path, base_content=base, new_content=content, summary=summary)
            s.add(edit)
            await s.flush()
            view = edit_view(edit)
            ev = self._event(
                s,
                attempt_id,
                "edit.proposed",
                {"edit_id": edit.id, "path": path, "summary": summary, "diff": view["diff"]},
            )
            await s.commit()
        self._publish(ev)
        return view

    async def decide_edit(self, attempt_id: str, edit_id: int, accept: bool, reason: str = "") -> dict[str, Any]:
        published = []
        stale = False
        async with self._locks[attempt_id], self._sessions() as s:
            attempt = await self._active(s, attempt_id)
            edit = await s.get(FileEdit, edit_id)
            if edit is None or edit.attempt_id != attempt_id:
                raise NotFound(f"Правка {edit_id} не найдена")
            if edit.status != "pending":
                raise Conflict(f"Правка #{edit_id} уже обработана: {edit.status}")
            edit.decided_at = utcnow()
            payload = {"edit_id": edit.id, "path": edit.path}
            if not accept:
                edit.status = "rejected"
                edit.reason = reason
                _add_note(attempt, f"кандидат отклонил правку #{edit.id} в {edit.path}" + (f": {reason}" if reason else ""))
                published.append(self._event(s, attempt_id, "edit.rejected", {**payload, "reason": reason}))
            elif attempt.files.get(edit.path) != edit.base_content:
                edit.status = "stale"
                stale = True
                published.append(self._event(s, attempt_id, "edit.stale", payload))
            else:
                edit.status = "accepted"
                attempt.files = {**attempt.files, edit.path: edit.new_content}
                _add_note(attempt, f"кандидат принял правку #{edit.id} в {edit.path}")
                published.append(self._event(s, attempt_id, "edit.accepted", payload))
                published += await self._mark_stale(s, attempt_id, edit.path)
            await s.commit()
        for ev in published:
            self._publish(ev)
        if stale:
            raise Conflict(f"Файл {edit.path} изменился после того, как ассистент предложил правку — попросите обновить её")
        return edit_view(edit)

    async def file_snapshot(self, attempt_id: str) -> dict[str, str]:
        async with self._sessions() as s:
            return dict((await self._get(s, attempt_id)).files)

    # --- тесты ---

    async def run_tests(self, attempt_id: str, by: str) -> RunResult:
        async with self._sessions() as s:
            attempt = await self._active(s, attempt_id)
            files = dict(attempt.files)
            task = Task.model_validate(attempt.task)
        if task.run is None:
            raise BadRequest("В этой задаче нет тестов")
        result = await self._runner.run(files, task.run)
        async with self._locks[attempt_id], self._sessions() as s:
            attempt = await self._get(s, attempt_id)
            if by == "candidate":
                _add_note(attempt, "кандидат запустил тесты: " + ("прошли" if result.passed else "упали"))
            ev = self._event(
                s,
                attempt_id,
                "tests.run",
                {
                    "by": by,
                    "passed": result.passed,
                    "exit_code": result.exit_code,
                    "timed_out": result.timed_out,
                    "duration_ms": result.duration_ms,
                    "output": result.summary(),
                },
            )
            await s.commit()
        self._publish(ev)
        return result

    # --- для ассистента ---

    async def begin_assistant_turn(self, attempt_id: str, text: str) -> AssistantContext:
        async with self._locks[attempt_id], self._sessions() as s:
            attempt = await self._active(s, attempt_id)
            notes = list(attempt.notes)
            attempt.notes = []
            ev = self._event(s, attempt_id, "assistant.user_message", {"text": text})
            await s.commit()
        self._publish(ev)
        return AssistantContext(
            Task.model_validate(attempt.task), list(attempt.assistant_history), notes, attempt.category, attempt.level
        )

    async def finish_assistant_turn(
        self,
        attempt_id: str,
        history: list[dict[str, Any]],
        *,
        reply: str | None = None,
        edit_ids: list[int] | None = None,
        error: str | None = None,
    ) -> None:
        # Без проверки на активность: ответ, начатый до конца таймера, сохраняем.
        async with self._locks[attempt_id], self._sessions() as s:
            attempt = await self._get(s, attempt_id)
            attempt.assistant_history = history
            if error is not None:
                ev = self._event(s, attempt_id, "assistant.error", {"error": error})
            else:
                ev = self._event(s, attempt_id, "assistant.message", {"text": reply or "", "edit_ids": edit_ids or []})
            await s.commit()
        self._publish(ev)

    async def log_tool(self, attempt_id: str, tool: str, args: dict[str, Any], result: str) -> None:
        async with self._sessions() as s:
            ev = self._event(s, attempt_id, "assistant.tool", {"tool": tool, "args": args, "result": result})
            await s.commit()
        self._publish(ev)

    def notify(self, attempt_id: str, message: dict[str, Any]) -> None:
        self._bus.publish(attempt_id, message)

    # --- внутреннее ---

    async def _get(self, s: AsyncSession, attempt_id: str) -> Attempt:
        attempt = await s.get(Attempt, attempt_id)
        if attempt is None:
            raise NotFound(f"Попытка {attempt_id} не найдена")
        return attempt

    async def _expire_if_due(self, s: AsyncSession, attempt: Attempt) -> SessionEvent | None:
        if attempt.status != "active" or utcnow() <= attempt.deadline_at:
            return None
        attempt.status = "expired"
        attempt.submitted_at = attempt.deadline_at
        ev = self._event(s, attempt.id, "attempt.expired", {})
        await s.commit()
        return ev

    async def _active(self, s: AsyncSession, attempt_id: str) -> Attempt:
        attempt = await self._get(s, attempt_id)
        expired = await self._expire_if_due(s, attempt)
        if expired:
            self._publish(expired)
        if attempt.status != "active":
            raise AttemptClosed("Время вышло" if attempt.status == "expired" else "Решение уже сдано")
        return attempt

    async def _mark_stale(self, s: AsyncSession, attempt_id: str, path: str) -> list[SessionEvent]:
        """Файл изменился — непринятые правки к нему больше не применимы."""
        pending = (
            await s.scalars(
                select(FileEdit).where(
                    FileEdit.attempt_id == attempt_id, FileEdit.path == path, FileEdit.status == "pending"
                )
            )
        ).all()
        events = []
        for edit in pending:
            edit.status = "stale"
            edit.decided_at = utcnow()
            events.append(self._event(s, attempt_id, "edit.stale", {"edit_id": edit.id, "path": path}))
        return events

    def _event(self, s: AsyncSession, attempt_id: str, type_: str, payload: dict[str, Any]) -> SessionEvent:
        ev = SessionEvent(attempt_id=attempt_id, type=type_, payload=payload, created_at=utcnow())
        s.add(ev)
        return ev

    def _publish(self, ev: SessionEvent) -> None:
        self._bus.publish(ev.attempt_id, {"type": "event", "event": event_view(ev)})


def _check_size(content: str) -> None:
    if len(content) > MAX_FILE_CHARS:
        raise BadRequest(f"Файл больше {MAX_FILE_CHARS} символов")


def _add_note(attempt: Attempt, note: str) -> None:
    if note not in attempt.notes:
        attempt.notes = [*attempt.notes, note]
