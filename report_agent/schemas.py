"""Contracts for the final report agent.

The report agent consolidates every earlier stage (features, patents,
prosecutor, defender, risk matrix, design-arounds, redesign images) into a
single structured report. The model only writes the *synthesis* fields
(:class:`ReportNarrative`); the passthrough sections are assembled
deterministically in code and the legal disclaimer is a fixed constant.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

LEGAL_DISCLAIMER = (
    "This analysis is AI-generated informational research and is not legal "
    "advice. Patent scope, claim construction, infringement, validity, and "
    "freedom-to-operate determinations require review by qualified patent "
    "counsel."
)


class ReportNarrative(BaseModel):
    """The only part of the report the LLM produces."""

    executive_summary: str = ""
    key_risks: list[str] = Field(default_factory=list)
    important_uncertainties: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    attorney_questions: list[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    """The consolidated report returned to the API / UI."""

    # synthesis (from ReportNarrative)
    executive_summary: str = ""
    key_risks: list[str] = Field(default_factory=list)
    important_uncertainties: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    attorney_questions: list[str] = Field(default_factory=list)

    # passthrough (assembled in code)
    product_summary: str = ""
    extracted_features: list[dict] = Field(default_factory=list)
    top_patents: list[dict] = Field(default_factory=list)
    prosecutor_findings: dict = Field(default_factory=dict)
    defender_findings: dict = Field(default_factory=dict)
    claim_mappings: list[dict] = Field(default_factory=list)
    risk_matrix: dict = Field(default_factory=dict)
    design_alternatives: list[dict] = Field(default_factory=list)
    redesign_concepts: list[dict] = Field(default_factory=list)

    legal_disclaimer: str = LEGAL_DISCLAIMER


__all__ = ["ReportNarrative", "FinalReport", "LEGAL_DISCLAIMER"]
