"""PatentGate - Agent 1 local HTTP API server.

Exposes the existing OpenAI-only knowledge-based Agent 1 pipeline over HTTP.
This server does NOT perform web search, does NOT use Gemini, and does NOT
access any external patent API. It reuses the existing ``run_agent1``
orchestrator and writes the same structured JSON result to ``results.json``.

Start with:
    uvicorn server:app --reload
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

from . import mask_secrets, run_agent1

RESULTS_FILE = "results.json"
# The project root (parent of the agent1/ package), where results.json lives.
RESULTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="PatentGate Agent 1", version="1.0.0")
load_dotenv()


class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze."""

    product_description: str = Field(..., min_length=1)


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    """Run Agent 1 on a product description and return the same structured
    JSON that ``main.py`` produces, also saving it to ``results.json``.
    """
    description = request.product_description.strip()
    if not description:
        return {"status": "error", "error": "Product description is empty."}

    try:
        result = run_agent1(description, load_env=False)
    except Exception as exc:
        # Never leak secrets/stack traces; return a clean structured error.
        return {
            "status": "error",
            "error": f"Agent 1 failed: {type(exc).__name__}: {mask_secrets(str(exc))}",
        }

    payload = json.dumps(result.model_dump(), indent=2, ensure_ascii=False)

    results_path = os.path.join(RESULTS_DIR, RESULTS_FILE)
    with open(results_path, "w", encoding="utf-8") as handle:
        handle.write(payload + "\n")

    return json.loads(payload)