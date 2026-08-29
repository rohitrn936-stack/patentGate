from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def get_async_database_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+asyncpg")
    elif url.drivername == "postgres":
        url = url.set(drivername="postgresql+asyncpg")

    # asyncpg receives SSL through connect_args; libpq-only URL keys are removed.
    url = url.difference_update_query(["sslmode", "channel_binding"])
    return url.render_as_string(hide_password=False)


settings = get_settings()
engine = create_async_engine(
    get_async_database_url(settings.database_url),
    pool_pre_ping=True,
    connect_args={"ssl": True},
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def verify_database_connection() -> bool:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return True
