"""Pydantic schemas for Agent 3 (Defender).

Agent 3 consumes Agent 2's (Prosecutor's) output and produces a defense
analysis for Agent 4 to consume. These models define the JSON contract and are
intentionally tolerant of Agent 2's evolving input shape.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high"]


class Distinction(BaseModel):
    """A difference between the claimed invention and the prior art."""

    claim_element: str = ""
    distinction: str = ""
    reasoning: str = ""


class PriorArtGap(BaseModel):
    """An area where prior art appears not to cover the claimed invention."""

    claim_element: str = ""
    gap: str = ""
    reasoning: str = ""


class WeakClaimElement(BaseModel):
    """A claim element that may be challenged or is weakly supported."""

    claim_element: str = ""
    reasoning: str = ""
    risk: Severity = "medium"


class DefenseAnalysis(BaseModel):
    """The core defense analysis produced by Agent 3."""

    distinctions: list[Distinction] = Field(default_factory=list)
    prior_art_gaps: list[PriorArtGap] = Field(default_factory=list)
    weak_claim_elements: list[WeakClaimElement] = Field(default_factory=list)
    overall_assessment: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    disclaimer: str = (
        "This is an AI-based analysis and is NOT a verified patent search or "
        "legal opinion."
    )


class DefenderResponse(BaseModel):
    """Final Agent 3 response envelope."""

    status: str = "ok"
    errors: list[str] = Field(default_factory=list)
    defense_analysis: DefenseAnalysis = Field(default_factory=DefenseAnalysis)


class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze.

    Agent 2's output is passed under ``agent2_output``. The remaining fields are
    optional and ignored otherwise, so a plain JSON body from Agent 2 is also
    accepted.
    """

    agent2_output: dict | None = None


__all__ = [
    "Severity",
    "Distinction",
    "PriorArtGap",
    "WeakClaimElement",
    "DefenseAnalysis",
    "DefenderResponse",
    "AnalyzeRequest",
]