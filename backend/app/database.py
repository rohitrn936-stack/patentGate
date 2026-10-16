from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def get_async_database_url(database_url: str) -> str:
    """Normalize a database URL to an async driver.

    - ``postgres`` / ``postgresql`` -> ``postgresql+asyncpg``
    - ``sqlite`` -> ``sqlite+aiosqlite``
    - anything already async is left untouched.
    """

    url = make_url(database_url)
    if url.drivername in {"postgresql", "postgres"}:
        url = url.set(drivername="postgresql+asyncpg")
        # asyncpg takes SSL via connect_args; strip libpq-only query keys.
        url = url.difference_update_query(["sslmode", "channel_binding"])
    elif url.drivername == "sqlite":
        url = url.set(drivername="sqlite+aiosqlite")
    return url.render_as_string(hide_password=False)


def _postgres_needs_ssl() -> bool:
    """Require TLS to Postgres unless it is an obviously local host."""

    url = make_url(get_settings().database_url)
    host = (url.host or "").lower()
    local = host in {"", "localhost", "127.0.0.1", "::1"} or host.endswith(".local")
    return not local


def _engine_kwargs(async_url: str) -> dict:
    kwargs: dict = {"pool_pre_ping": True}
    if make_url(async_url).get_backend_name() == "postgresql" and _postgres_needs_ssl():
        kwargs["connect_args"] = {"ssl": True}
    return kwargs


_async_url = get_async_database_url(get_settings().database_url)
engine = create_async_engine(_async_url, **_engine_kwargs(_async_url))
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def verify_database_connection() -> bool:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return True


async def create_all_tables() -> None:
    """Create tables directly from the models (used for SQLite dev/tests).

    Postgres deployments should use Alembic migrations instead.
    """

    from app import models  # noqa: F401  (register mappers)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
