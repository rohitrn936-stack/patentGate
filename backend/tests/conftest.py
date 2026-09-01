"""Backend test harness: SQLite, no network, rate limiting disabled."""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

# Configure the app BEFORE importing anything under app.*
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".sqlite3", prefix="patentgate_test_")
os.close(_DB_FD)
os.environ.update(
    APP_ENV="test",
    DATABASE_URL=f"sqlite+aiosqlite:///{_DB_PATH}",
    JWT_SECRET="test-secret-" + "x" * 40,
    ACCESS_TOKEN_EXPIRE_MINUTES="30",
    RATE_LIMIT_ENABLED="false",
    IN_PROCESS_AGENTS="true",
    LLM_PROVIDER="fake",
    LOG_JSON="false",
)

import httpx  # noqa: E402
import llm.testing  # noqa: E402,F401  (registers the FakeProvider)
from httpx import ASGITransport  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.rate_limit import reset as reset_rate_limits  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _dispose_engine() -> AsyncIterator[None]:
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _schema() -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    reset_rate_limits()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_client(client: httpx.AsyncClient) -> AsyncIterator[tuple[httpx.AsyncClient, dict]]:
    resp = await client.post(
        "/api/auth/register",
        json={"name": "Ada", "email": "ada@example.com", "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client, resp.json()


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    try:
        os.remove(_DB_PATH)
    except OSError:
        pass
