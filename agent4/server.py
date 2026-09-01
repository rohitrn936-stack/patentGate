"""Agent 4 - Design-Around Engineer: standalone HTTP API (dev / LAN use).

Run from the repo root:
    uvicorn agent4.server:app --reload --port 8003
"""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from .agent import DesignEngineer
from .models import DesignOutput, DesignRequest

app = FastAPI(title="PatentGate Agent 4 - Design-Around Engineer", version="2.0.0")

_engineer: DesignEngineer | None = None


def _get_engineer() -> DesignEngineer:
    global _engineer
    if _engineer is None:
        _engineer = DesignEngineer()
    return _engineer


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "agent": "design-engineer"}


@app.post("/design", response_model=DesignOutput)
def design(request: DesignRequest) -> DesignOutput:
    return _get_engineer().generate(
        request.product.model_dump(),
        request.prosecutor.model_dump(),
        request.defender.model_dump(),
    )


@app.post("/design/stream")
def design_stream(request: DesignRequest) -> StreamingResponse:
    product = request.product.model_dump()
    prosecutor = request.prosecutor.model_dump()
    defender = request.defender.model_dump()

    def event_generator():
        yield f"event: status\ndata: {json.dumps({'status': 'started', 'agent': 'design-engineer'})}\n\n"
        try:
            for event in _get_engineer().stream(product, prosecutor, defender):
                yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
        yield f"event: complete\ndata: {json.dumps({'status': 'completed'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


__all__ = ["app"]
