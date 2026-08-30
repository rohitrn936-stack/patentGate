from typing import List, Optional, Any
from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str = ""
    description: str = ""
    features: List[str] = Field(default_factory=list)


class RiskClaim(BaseModel):
    patent_id: Optional[str] = None
    claim_id: Optional[str] = None
    risk_level: Optional[str] = None
    reason: Optional[str] = None


class ClaimElementMapping(BaseModel):
    patent_id: Optional[str] = None
    claim_id: Optional[str] = None
    claim_element: Optional[str] = None
    product_feature: Optional[str] = None
    strength: Optional[str] = None
    explanation: Optional[str] = None


class ConfidencePerPatent(BaseModel):
    patent_id: Optional[str] = None
    confidence: Optional[float] = None
    explanation: Optional[str] = None


class ProsecutorOutput(BaseModel):
    risk_claims: List[RiskClaim] = Field(default_factory=list)
    claim_element_mappings: List[ClaimElementMapping] = Field(default_factory=list)
    confidence_per_patent: List[ConfidencePerPatent] = Field(default_factory=list)


class Distinction(BaseModel):
    patent_id: Optional[str] = None
    claim_id: Optional[str] = None
    distinction: Optional[str] = None


class PriorArtGap(BaseModel):
    patent_id: Optional[str] = None
    claim_id: Optional[str] = None
    gap: Optional[str] = None


class WeakClaimElement(BaseModel):
    patent_id: Optional[str] = None
    claim_id: Optional[str] = None
    claim_element: Optional[str] = None
    weakness: Optional[str] = None


class DefenderOutput(BaseModel):
    distinctions: List[Distinction] = Field(default_factory=list)
    prior_art_gaps: List[PriorArtGap] = Field(default_factory=list)
    weak_claim_elements: List[WeakClaimElement] = Field(default_factory=list)


class DesignRequest(BaseModel):
    product: Product
    prosecutor: ProsecutorOutput = Field(default_factory=ProsecutorOutput)
    defender: DefenderOutput = Field(default_factory=DefenderOutput)


class AlternativeDesign(BaseModel):
    id: int
    description: str
    avoids_claim_element: str
    changes_from_original: List[str] = Field(default_factory=list)
    tradeoff: str
    why_it_differs: str
    risk_reduction_rationale: str
    design_generation_prompt: str


class DesignOutput(BaseModel):
    agent: str = "design-engineer"
    status: str = "completed"
    alternatives: List[AlternativeDesign] = Field(default_factory=list)
    legal_disclaimer: str = (
        "These engineering alternatives are not a determination of patent "
        "infringement or freedom to operate. Legal review by a qualified "
        "patent attorney is required."
    )


# ============================================================
# Image generation layer (DALL-E / OpenAI Images)
# ============================================================
#
# The image layer is a CONSUMER of Agent 4's DesignOutput. It accepts the
# complete Agent 4 JSON (agent / status / alternatives / legal_disclaimer),
# validates it, builds one image prompt per alternative, and generates one
# engineering concept image per alternative.

class DesignEngineerInput(DesignOutput):
    """The complete Agent 4 output that the image layer consumes."""


class GeneratedImage(BaseModel):
    alternative_id: int
    filename: str
    path: str = ""
    url: str = ""
    prompt: str = ""


class ImageGenerationError(BaseModel):
    alternative_id: int
    error: str


class DesignImageResponse(BaseModel):
    agent: str = "design-engineer"
    status: str = "completed"
    images: List[GeneratedImage] = Field(default_factory=list)
    errors: List[ImageGenerationError] = Field(default_factory=list)
    count: int = 0