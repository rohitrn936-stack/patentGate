"""Authenticated single-shot Agent 1 endpoint (feature extraction preview).

Runs Agent 1 in-process by default; set ``IN_PROCESS_AGENTS=false`` and
``AGENT1_SERVER_URL`` to proxy to a standalone Agent 1 server instead.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import get_settings
from app.dependencies.auth import get_current_user
from app.models import User
from app.rate_limit import AGENT_LIMIT
from app.schemas.agent1 import Agent1Request, Agent1Response

router = APIRouter(prefix="/api/agent1", tags=["agent1"])
logger = logging.getLogger("patentgate.agent1")


def _run_in_process(description: str) -> dict:
    from agent1 import mask_secrets, run_agent1

    try:
        return run_agent1(description, load_env=True).model_dump()
    except Exception as exc:  # noqa: BLE001 - surfaced as a structured error
        raise RuntimeError(mask_secrets(f"{type(exc).__name__}: {exc}")) from exc


async def _proxy_to_server(description: str) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.agent1_server_url}/analyze",
            json={"product_description": description},
        )
    resp.raise_for_status()
    return resp.json()


@router.post("", response_model=Agent1Response, dependencies=[AGENT_LIMIT])
async def call_agent1(
    payload: Agent1Request,
    current_user: User = Depends(get_current_user),
) -> Agent1Response:
    description = payload.input.strip()
    if not description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Product description is empty"
        )

    settings = get_settings()
    try:
        if settings.in_process_agents:
            result = await asyncio.to_thread(_run_in_process, description)
        else:
            result = await _proxy_to_server(description)
    except httpx.ConnectError:
        return Agent1Response(
            success=False,
            error=f"Cannot reach the Agent 1 server at {settings.agent1_server_url}",
        )
    except httpx.TimeoutException:
        return Agent1Response(success=False, error="Agent 1 request timed out")
    except Exception as exc:  # noqa: BLE001
        logger.warning("agent1 failed: %s", exc)
        return Agent1Response(success=False, error=f"Agent 1 failed: {exc}")

    if isinstance(result, dict) and result.get("status") == "error":
        return Agent1Response(success=False, error=result.get("error", "Agent 1 failed"))
    return Agent1Response(success=True, result=result)
