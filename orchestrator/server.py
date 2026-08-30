"""Orchestrator FastAPI server.

Exposes ``POST /run`` (execute Agent 2 -> Agent 3 -> Agent 4 iteration) and
``GET /health``.

Run (from the orchestrator directory):
    uvicorn server:app --reload --port 8004

Run (from the patentGate directory):
    uvicorn orchestrator.server:app --reload --port 8004
"""

from __future__ import annotations

from typing import Any, Optional

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .orchestrator import Orchestrator
from .schemas import RunResult

app = FastAPI(title="PatentGate Orchestrator", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run")
async def run(request: Request) -> JSONResponse:
    """Run the multi-agent pipeline."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "final_status": "error",
                "errors": ["Request body must be valid JSON."],
            },
        )

    product = body.get("product") if isinstance(body, dict) else None
    patents = body.get("patents") if isinstance(body, dict) else None

    orchestrator = Orchestrator()

    try:
        result = orchestrator.run(product, patents)
    except httpx.ConnectError as exc:
        result = RunResult(
            final_status="error",
            errors=[f"Could not connect to an agent: {exc}"],
        )
    except httpx.TimeoutException as exc:
        result = RunResult(
            final_status="error",
            errors=[f"Agent request timed out: {exc}"],
        )
    except Exception as exc:  # noqa: BLE001 - surface clean error to client
        result = RunResult(
            final_status="error",
            errors=[f"Orchestration failed: {exc}"],
        )

    return JSONResponse(content=result.model_dump())


__all__ = ["app"]