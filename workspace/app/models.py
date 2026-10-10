from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, utcnow


class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Attempt(Base):
    """Одна сессия решения задачи кандидатом."""

    __tablename__ = "attempts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    candidate_id: Mapped[str] = mapped_column(String(64), index=True)
    # На какую категорию и грейд кандидат проходит тест: задача может подходить под несколько
    category: Mapped[str] = mapped_column(String(64))
    level: Mapped[str] = mapped_column(String(16))
    # active → submitted | expired
    status: Mapped[str] = mapped_column(String(16), default="active")
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    deadline_at: Mapped[datetime]
    submitted_at: Mapped[datetime | None] = mapped_column(default=None)
    # Снимок задачи на момент старта: оценка должна видеть ровно ту версию, которую решал кандидат.
    task: Mapped[dict[str, Any]] = mapped_column(JSON)
    # Текущие файлы решения: путь → содержимое
    files: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    # Переписка с ассистентом в формате llm.types.Message — для следующих запросов к модели
    assistant_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    # Действия кандидата, о которых ассистент ещё не знает (принял правку, поправил файл)
    notes: Mapped[list[str]] = mapped_column(JSON, default=list)


class FileEdit(Base):
    """Правка, предложенная ассистентом. Применяется только после решения кандидата."""

    __tablename__ = "file_edits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), index=True)
    path: Mapped[str] = mapped_column(String(200))
    # Содержимое файла, от которого считалась правка; None — ассистент создаёт новый файл
    base_content: Mapped[str | None] = mapped_column(Text, default=None)
    new_content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    # pending → accepted | rejected | stale (файл успел измениться)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(default=None)


class SessionEvent(Base):
    """Журнал сессии: всё, что делал кандидат и ассистент. По нему потом идёт оценка процесса."""

    __tablename__ = "session_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Grading(Base):
    """Итог проверки попытки. Один на попытку; повторная проверка перезаписывает его."""

    __tablename__ = "gradings"

    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), primary_key=True)
    # pending → running → done | failed
    status: Mapped[str] = mapped_column(String(16), default="pending")
    error: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[int | None] = mapped_column(default=None)
    max_score: Mapped[int | None] = mapped_column(default=None)
    # None — ни один порог не пройден
    grade: Mapped[str | None] = mapped_column(String(16), default=None)
    # Прогоны судьи дали разный грейд — засчитан нижний
    unstable: Mapped[bool] = mapped_column(default=False)
    # Итог по критериям, по прогонам и результат автотестов — то, что показываем кандидату и работодателю
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class CriterionVerdict(Base):
    """Вердикт судьи по одному критерию в одном прогоне — сырые данные проверки."""

    __tablename__ = "criterion_verdicts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), index=True)
    run: Mapped[int]
    criterion_id: Mapped[str] = mapped_column(String(64))
    # Что сказал судья: yes | partial | no
    verdict: Mapped[str] = mapped_column(String(8))
    # Что засчитано после проверки цитаты и правил критерия
    counted: Mapped[str] = mapped_column(String(8))
    evidence: Mapped[str] = mapped_column(Text, default="")
    evidence_found: Mapped[bool] = mapped_column(default=False)
    comment: Mapped[str] = mapped_column(Text, default="")


class AttemptReview(Base):
    """Решение человека по попытке, помеченной системой (например, уход со вкладки). Принимается один раз."""

    __tablename__ = "attempt_reviews"

    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), primary_key=True)
    reviewer: Mapped[str] = mapped_column(String(120))
    # True — попытка аннулирована: грейд, полученный ею, снят, тесты кандидата заморожены
    annulled: Mapped[bool]
    comment: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime] = mapped_column(default=utcnow)


class GradeRecord(Base):
    """Текущий подтверждённый грейд кандидата в категории."""

    __tablename__ = "grade_records"

    candidate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category: Mapped[str] = mapped_column(String(64), primary_key=True)
    grade: Mapped[str] = mapped_column(String(16))
    score: Mapped[int]
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"))
    confirmed_at: Mapped[datetime]
    next_change_at: Mapped[datetime]


class TaskGeneration(Base):
    """Заявка на генерацию задачи: что просили, как прошли проверки, какая задача получилась."""

    __tablename__ = "task_generations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    request: Mapped[dict[str, Any]] = mapped_column(JSON)
    # pending → running → done | failed
    status: Mapped[str] = mapped_column(String(16), default="pending")
    task_id: Mapped[str | None] = mapped_column(String(64), default=None)
    error: Mapped[str] = mapped_column(Text, default="")
    # Попытки генерации: какие проверки не прошли — модели их показывают, и она исправляет
    report: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    # Последний черновик — чтобы посмотреть, что именно не прошло
    draft: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class LLMCall(Base):
    """Журнал вызовов моделей: какой промпт какой версии что ответил, сколько ждали в очереди и токенов."""

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scenario: Mapped[str] = mapped_column(String(40))
    channel: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(40), default="")
    attempt_id: Mapped[str | None] = mapped_column(String(32), index=True, default=None)
    status: Mapped[str] = mapped_column(String(16))
    error: Mapped[str] = mapped_column(Text, default="")
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    cached_tokens: Mapped[int] = mapped_column(default=0)
    queue_ms: Mapped[int] = mapped_column(default=0)
    duration_ms: Mapped[int] = mapped_column(default=0)
    request: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    response: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
