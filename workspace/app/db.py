from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """Время везде в UTC без tzinfo: SQLite не хранит зону, так поведение одинаковое и в Postgres."""
    return datetime.now(UTC).replace(tzinfo=None)


def make_engine(url: str) -> AsyncEngine:
    return create_async_engine(url)


def make_sessions(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_tables(engine: AsyncEngine) -> None:
    # Миграций на хакатоне нет: таблицы создаются при старте, при смене схемы — удалить БД.
    from app import models  # noqa: F401  регистрирует таблицы в Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
