"""Agent 3 - Defender: local HTTP API server.

Consumes Agent 2's (Prosecutor's) JSON and returns a defense analysis for
Agent 4 to consume.

Run (from the agent3 directory):
    uvicorn server:app --reload --port 8002

Run (from the patentGate directory):
    uvicorn agent3.server:app --reload --port 8002
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, Request

from .agent import Defender
from .schemas import AnalyzeRequest, DefenderResponse

app = FastAPI(title="PatentGate Agent 3 - Defender", version="1.0.0")

# Lazily-created Defender so the server can start without a valid API key and
# tests can inject a fake. Created on first /analyze call.
_defender: Optional[Defender] = None


def _get_defender() -> Defender:
    global _defender
    if _defender is None:
        _defender = Defender()
    return _defender


def _extract_agent2_payload(body: Any) -> dict:
    """Tolerantly extract the Agent 2 payload from the request body.

    Agent 2's exact structure may evolve, so accept either a raw JSON object
    (used directly) or an object wrapped under ``agent2_output``.
    """
    if isinstance(body, dict):
        wrapped = body.get("agent2_output")
        if isinstance(wrapped, dict) and wrapped:
            return wrapped
        return body
    return {}


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(request: Request) -> dict:
    """Run Agent 3 defense analysis over Agent 2's output."""
    body = await request.json()

    payload = _extract_agent2_payload(body)
    if not payload:
        return (
            DefenderResponse(
                status="error",
                errors=["No Agent 2 output provided."],
            ).model_dump()
        )

    defender = _get_defender()

    try:
        analysis = defender.analyze(payload)
    except RuntimeError as exc:
        return (
            DefenderResponse(
                status="error",
                errors=[str(exc)],
            ).model_dump()
        )
    except ValueError as exc:
        return (
            DefenderResponse(
                status="error",
                errors=[str(exc)],
            ).model_dump()
        )

    return DefenderResponse(
        status="ok",
        errors=[],
        defense_analysis=analysis,
    ).model_dump()


__all__ = ["app"]