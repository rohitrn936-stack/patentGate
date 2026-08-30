"""Pydantic schemas for the Orchestrator.

The orchestrator coordinates Agent 2 -> Agent 3 -> Agent 4 over HTTP/JSON and
decides when to stop iterating. These models define the ``POST /run`` request
and its response. No agent implementation classes are imported.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    """Initial input for a run.

    Mirrors Agent 2's request contract:
    - ``product``: {name, description, features[]}
    - ``patents``: list of {id, summary, claims} (Agent 2 expects exactly 5).
    """

    product: Optional[Any] = None
    patents: Optional[list[Any]] = None
    # Allow arbitrary extra fields so the orchestrator remains tolerant of
    # Agent 2's input shape evolving.
    extra: dict[str, Any] = Field(default_factory=dict, exclude=True)


class IterationRecord(BaseModel):
    """A single Agent 2 -> Agent 3 -> Agent 4 iteration, preserved verbatim."""

    iteration: int
    agent2_output: Any = None
    agent3_output: Any = None
    agent4_output: Any = None
    stop_reason: str = ""


class RunResult(BaseModel):
    """The final response of ``POST /run``."""

    final_status: str = "ok"
    iteration_count: int = 0
    final_agent2_output: Any = None
    final_agent3_output: Any = None
    final_agent4_output: Any = None
    iteration_history: list[IterationRecord] = Field(default_factory=list)
    next_step: str = ""
    stop_reason: str = ""
    errors: list[str] = Field(default_factory=list)


__all__ = ["RunRequest", "IterationRecord", "RunResult"]