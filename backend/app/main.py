from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import create_all_tables, verify_database_connection
from app.errors import register_exception_handlers
from app.logging_config import configure_logging
from app.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from app.routes import agent1, analyses, auth, products

settings = get_settings()
configure_logging(settings.log_level, settings.log_json)
logger = logging.getLogger("patentgate.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For SQLite (local dev / tests) create tables on boot. Postgres uses Alembic.
    if settings.database_url.startswith("sqlite"):
        await create_all_tables()
    logger.info("startup", extra={"env": settings.app_env, "providers_in_process": settings.in_process_agents})
    yield


app = FastAPI(title="PatentGate API", version="0.2.0", lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(analyses.router)
app.include_router(agent1.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
async def health_db() -> dict[str, str]:
    try:
        await verify_database_connection()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="Database connection failed") from exc
    return {"status": "ok", "database": "connected"}
