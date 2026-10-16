"""PatentGate - Agent 1 standalone HTTP API server (dev / LAN use).

Exposes the knowledge-based Agent 1 pipeline over HTTP. The LLM provider is
chosen by environment config (see :mod:`llm.config`) - OpenAI, Anthropic,
Gemini, OpenRouter or a local server. This server performs no web search and no
external patent retrieval. It reuses ``run_agent1`` and writes the structured
JSON result to ``results.json``.

The primary integration path is now in-process via the backend
(``IN_PROCESS_AGENTS=true``); this server is kept for parity and local testing.

Start from the repo root:
    uvicorn agent1.server:app --reload --port 8001
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