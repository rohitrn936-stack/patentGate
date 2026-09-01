"""Pydantic schemas for Agent 1 (feature extraction + knowledge analysis).

These models define the exact JSON contract that Agent 1 produces so that
Agents 2 (Prosecutor) and 3 (Defender) can consume it later.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Product(BaseModel):
    """The analyzed product, as understood by Agent 1."""

    name: str = ""
    summary: str = ""


class Component(BaseModel):
    """A physical or logical building block of the product."""

    id: str = ""
    name: str
    description: str = ""
    function: str = ""


class Feature(BaseModel):
    """A single technical feature.

    ``evidence_source`` distinguishes facts stated by the user from
    observations made from an image from engineering assumptions.
    """

    id: str
    name: str
    description: str = ""
    component: str = ""
    function: str = ""
    evidence: str = ""
    evidence_source: Literal["user_stated", "image_observation", "assumption"] = (
        "user_stated"
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class TechnicalConcept(BaseModel):
    """A broader technical concept/domain the product relies on."""

    name: str
    description: str = ""


class Mechanism(BaseModel):
    """A working principle or mechanism used by the product."""

    name: str
    description: str = ""
    purpose: str = ""


class Material(BaseModel):
    """A material the product is made of (facts only, no invention)."""

    name: str
    purpose: str = ""


class Interface(BaseModel):
    """A communication or electrical interface."""

    name: str
    interface_type: str = ""
    protocol: str = ""
    description: str = ""


class SoftwareFeature(BaseModel):
    """A software/software-related technical behavior."""

    name: str
    description: str = ""


class Assumption(BaseModel):
    """An assumption Agent 1 made while interpreting the input."""

    message: str
    reason: str = ""


class FeatureExtraction(BaseModel):
    """Validated output of Job 1 (OpenAI technical feature extraction)."""

    product: Product = Field(default_factory=Product)
    components: list[Component] = Field(default_factory=list)
    features: list[Feature] = Field(default_factory=list)
    technical_concepts: list[TechnicalConcept] = Field(default_factory=list)
    mechanisms: list[Mechanism] = Field(default_factory=list)
    materials: list[Material] = Field(default_factory=list)
    interfaces: list[Interface] = Field(default_factory=list)
    software_features: list[SoftwareFeature] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)


class SimilarConcept(BaseModel):
    """A similar known concept/technology the model recognizes from its
    learned knowledge (NOT a verified patent search result).

    No patent identifiers (publication/patent numbers, URLs, filing dates) are
    ever fabricated. This describes prior-art "concepts" the model already
    knows about, without claiming any specific, real patent was found.
    """

    name: str
    why_similar: str = ""
    matching_features: list[str] = Field(default_factory=list)
    differences: str = ""
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)


class KnowledgeAnalysis(BaseModel):
    """Job 2 output: knowledge-based similarity analysis.

    This is produced from the model's learned knowledge only. It is NOT a
    verified patent search and must be labeled as such.
    """

    invention: str = ""
    technical_features: list[str] = Field(default_factory=list)
    similar_known_concepts: list[SimilarConcept] = Field(default_factory=list)
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    similarity_explanation: str = ""
    potentially_overlapping_areas: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    disclaimer: str = (
        "This analysis is based on the model's learned knowledge and is NOT a "
        "verified patent search."
    )


class Agent1Output(BaseModel):
    """Final output of Agent 1, validated end-to-end."""

    status: str = "ok"
    errors: list[str] = Field(default_factory=list)

    product: Product = Field(default_factory=Product)
    components: list[Component] = Field(default_factory=list)
    features: list[Feature] = Field(default_factory=list)
    technical_concepts: list[TechnicalConcept] = Field(default_factory=list)
    mechanisms: list[Mechanism] = Field(default_factory=list)
    materials: list[Material] = Field(default_factory=list)
    interfaces: list[Interface] = Field(default_factory=list)
    software_features: list[SoftwareFeature] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)

    analysis: KnowledgeAnalysis = Field(default_factory=KnowledgeAnalysis)


__all__ = [
    "Product",
    "Component",
    "Feature",
    "TechnicalConcept",
    "Mechanism",
    "Material",
    "Interface",
    "SoftwareFeature",
    "Assumption",
    "FeatureExtraction",
    "SimilarConcept",
    "KnowledgeAnalysis",
    "Agent1Output",
]