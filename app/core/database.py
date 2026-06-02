from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, MappedColumn, mapped_column
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    pass


def build_engine(url: str | None = None, *, testing: bool = False) -> AsyncEngine:
    db_url = url or settings.DATABASE_URL
    kwargs: dict[str, Any] = {
        "echo": settings.DEBUG,
        "future": True,
    }
    if testing:
        kwargs["poolclass"] = NullPool
    else:
        kwargs.update(
            {
                "pool_size": settings.DATABASE_POOL_SIZE,
                "max_overflow": settings.DATABASE_MAX_OVERFLOW,
                "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            }
        )
    return create_async_engine(db_url, **kwargs)


engine: AsyncEngine = build_engine()

AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database connection failed", error=str(exc))
        return False


async def close_db() -> None:
    await engine.dispose()
    logger.info("Database connections closed")
