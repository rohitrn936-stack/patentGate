from typing import List
from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str
    description: str = ""
    features: List[str]


class Patent(BaseModel):
    id: str
    summary: str
    claims: str


class RiskClaim(BaseModel):
    patent_id: str
    claim_id: str
    risk_level: str
    reason: str


class ClaimMapping(BaseModel):
    patent_id: str
    claim_id: str
    claim_element: str
    product_feature: str
    strength: str
    explanation: str


class PatentConfidence(BaseModel):
    patent_id: str
    confidence: float = Field(ge=0, le=1)
    explanation: str


class ProsecutorOutput(BaseModel):
    risk_claims: List[RiskClaim]
    claim_element_mappings: List[ClaimMapping]
    confidence_per_patent: List[PatentConfidence]


class ProsecutorRequest(BaseModel):
    product: Product
    patents: List[Patent] = Field(min_length=5, max_length=5)