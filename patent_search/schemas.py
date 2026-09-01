"""Pydantic contracts for the patent search layer.

The search layer sits between Agent 1 (feature extraction) and Agents 2/3. It
turns Agent 1's technical features into search queries, runs them against one or
more prior-art sources, and returns up to five normalized, de-duplicated,
relevance-ranked patent hits.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PatentHit(BaseModel):
    """One normalized prior-art result.

    Every source (PatentsView, Google Patents, Tavily, or the offline
    concept-derived fallback) is mapped onto this shape so downstream agents
    never see a source-specific payload.
    """

    patent_number: str = ""
    title: str = ""
    abstract: str = ""
    filing_date: str | None = None
    publication_date: str | None = None
    inventors: list[str] = Field(default_factory=list)
    assignee: str | None = None
    claims: str = ""
    source: str = ""
    source_url: str = ""
    relevance_score: float = Field(default=0.0, ge=0.0)
    matching_features: list[str] = Field(default_factory=list)

    def as_agent_patent(self) -> dict:
        """Shape expected by Agent 2 (``{"id", "summary", "claims"}``)."""

        summary = self.abstract or self.title
        return {
            "id": self.patent_number or self.title or "UNKNOWN",
            "summary": summary,
            "claims": self.claims
            or f"{self.title}. {self.abstract}".strip(". ").strip(),
        }


class PatentSearchResult(BaseModel):
    """Everything the search layer produces for one analysis."""

    queries: list[str] = Field(default_factory=list)
    patents: list[PatentHit] = Field(default_factory=list)
    sources_used: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


__all__ = ["PatentHit", "PatentSearchResult"]
