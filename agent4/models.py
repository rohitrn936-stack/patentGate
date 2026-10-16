from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str = ""
    description: str = ""
    features: list[str] = Field(default_factory=list)


class RiskClaim(BaseModel):
    patent_id: str | None = None
    claim_id: str | None = None
    risk_level: str | None = None
    reason: str | None = None


class ClaimElementMapping(BaseModel):
    patent_id: str | None = None
    claim_id: str | None = None
    claim_element: str | None = None
    product_feature: str | None = None
    strength: str | None = None
    explanation: str | None = None


class ConfidencePerPatent(BaseModel):
    patent_id: str | None = None
    confidence: float | None = None
    explanation: str | None = None


class ProsecutorOutput(BaseModel):
    risk_claims: list[RiskClaim] = Field(default_factory=list)
    claim_element_mappings: list[ClaimElementMapping] = Field(default_factory=list)
    confidence_per_patent: list[ConfidencePerPatent] = Field(default_factory=list)


class Distinction(BaseModel):
    patent_id: str | None = None
    claim_id: str | None = None
    distinction: str | None = None


class PriorArtGap(BaseModel):
    patent_id: str | None = None
    claim_id: str | None = None
    gap: str | None = None


class WeakClaimElement(BaseModel):
    patent_id: str | None = None
    claim_id: str | None = None
    claim_element: str | None = None
    weakness: str | None = None


class DefenderOutput(BaseModel):
    distinctions: list[Distinction] = Field(default_factory=list)
    prior_art_gaps: list[PriorArtGap] = Field(default_factory=list)
    weak_claim_elements: list[WeakClaimElement] = Field(default_factory=list)


class DesignRequest(BaseModel):
    product: Product
    prosecutor: ProsecutorOutput = Field(default_factory=ProsecutorOutput)
    defender: DefenderOutput = Field(default_factory=DefenderOutput)


class AlternativeDesign(BaseModel):
    id: int
    description: str
    avoids_claim_element: str
    changes_from_original: list[str] = Field(default_factory=list)
    tradeoff: str
    why_it_differs: str
    risk_reduction_rationale: str
    design_generation_prompt: str


class DesignOutput(BaseModel):
    agent: str = "design-engineer"
    status: str = "completed"
    alternatives: list[AlternativeDesign] = Field(default_factory=list)
    legal_disclaimer: str = (
        "These engineering alternatives are not a determination of patent "
        "infringement or freedom to operate. Legal review by a qualified "
        "patent attorney is required."
    )