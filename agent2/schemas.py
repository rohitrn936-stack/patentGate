"""Pydantic schemas for Agent 2 (Prosecutor).

Agent 2 receives product features (from Agent 1) plus a set of patents and
argues where the patents' claim elements could potentially read on the product.
It never makes a legal determination.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str
    description: str = ""
    features: list[str] = Field(default_factory=list)


class Patent(BaseModel):
    id: str
    summary: str = ""
    claims: str = ""


class RiskClaim(BaseModel):
    patent_id: str = ""
    claim_id: str = ""
    risk_level: str = ""
    reason: str = ""


class ClaimElementMapping(BaseModel):
    patent_id: str = ""
    claim_id: str = ""
    claim_element: str = ""
    product_feature: str = ""
    strength: str = ""
    explanation: str = ""


class ConfidencePerPatent(BaseModel):
    patent_id: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    explanation: str = ""


class ProsecutorOutput(BaseModel):
    risk_claims: list[RiskClaim] = Field(default_factory=list)
    claim_element_mappings: list[ClaimElementMapping] = Field(default_factory=list)
    confidence_per_patent: list[ConfidencePerPatent] = Field(default_factory=list)


class ProsecutorRequest(BaseModel):
    product: Product
    #: A patent search typically returns ~5; at least one is required.
    patents: list[Patent] = Field(min_length=1, max_length=25)


class ProsecutorResponse(BaseModel):
    status: str = "ok"
    errors: list[str] = Field(default_factory=list)
    result: ProsecutorOutput = Field(default_factory=ProsecutorOutput)


__all__ = [
    "Product",
    "Patent",
    "RiskClaim",
    "ClaimElementMapping",
    "ConfidencePerPatent",
    "ProsecutorOutput",
    "ProsecutorRequest",
    "ProsecutorResponse",
]
