"""Agent 2 - Prosecutor: standalone HTTP API (dev / LAN use).

The primary integration path is in-process via the backend orchestrator; this
server exists for local testing and parity with the other agents.

Run from the repo root:
    uvicorn agent2.server:app --reload --port 8001
"""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from .agent import Prosecutor
from .schemas import ProsecutorRequest, ProsecutorResponse

app = FastAPI(title="PatentGate Agent 2 - Prosecutor", version="2.0.0")

_prosecutor: Prosecutor | None = None


def _get_prosecutor() -> Prosecutor:
    global _prosecutor
    if _prosecutor is None:
        _prosecutor = Prosecutor()
    return _prosecutor


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "agent": "prosecutor"}


@app.post("/analyze", response_model=ProsecutorResponse)
def analyze(request: ProsecutorRequest) -> ProsecutorResponse:
    product = request.product.model_dump()
    patents = [p.model_dump() for p in request.patents]
    try:
        result = _get_prosecutor().analyze(product, patents)
    except Exception as exc:  # noqa: BLE001 - return a clean structured error
        return ProsecutorResponse(status="error", errors=[str(exc)])
    return ProsecutorResponse(status="ok", result=result)


@app.post("/analyze/stream")
def analyze_stream(request: ProsecutorRequest) -> StreamingResponse:
    product = request.product.model_dump()
    patents = [p.model_dump() for p in request.patents]

    def event_generator():
        yield f"event: status\ndata: {json.dumps({'status': 'started', 'agent': 'prosecutor'})}\n\n"
        try:
            for event in _get_prosecutor().stream(product, patents):
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
