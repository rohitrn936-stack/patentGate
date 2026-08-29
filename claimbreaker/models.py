"""Pydantic contract emitted by ClaimBreaker Agent 1."""
from __future__ import annotations
import re
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class EvidenceType(StrEnum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    VISUAL = "visual"

class TechnicalFeature(BaseModel):
    """One atomic, technical product capability or structure."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(pattern=r"^F[1-9][0-9]*$", examples=["F1"])
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=5, max_length=700)
    technical_components: list[str] = Field(default_factory=list, max_length=12)
    function: str = Field(min_length=3, max_length=500)
    relationships: list[str] = Field(default_factory=list, max_length=12)
    evidence_type: EvidenceType

    @field_validator("relationships")
    @classmethod
    def relationships_are_feature_links(cls, values: list[str]) -> list[str]:
        pattern = re.compile(r"^F[1-9][0-9]*\s*->\s*F[1-9][0-9]*$")
        if invalid := [value for value in values if not pattern.fullmatch(value)]:
            raise ValueError(f"relationships must use 'F1 -> F2' form; got {invalid!r}")
        return values

class FeatureExtractionResult(BaseModel):
    """Validated, search-ready hand-off to the patent search layer."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    product_summary: str = Field(min_length=5, max_length=700)
    domain: list[str] = Field(min_length=1, max_length=6)
    features: list[TechnicalFeature] = Field(min_length=1, max_length=30)
    search_terms: list[str] = Field(min_length=1, max_length=50)
    technical_keywords: list[str] = Field(min_length=1, max_length=50)
    uncertainties: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_feature_references(self) -> "FeatureExtractionResult":
        ids = {feature.id for feature in self.features}
        if len(ids) != len(self.features):
            raise ValueError("feature IDs must be unique")
        for feature in self.features:
            for relationship in feature.relationships:
                left, right = (part.strip() for part in relationship.split("->", maxsplit=1))
                if left not in ids or right not in ids:
                    raise ValueError(f"relationship {relationship!r} references an unknown feature")
        return self


class PatentResult(BaseModel):
    """A normalized candidate discovered on the public Google Patents site."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    patent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    source: str = "Google Patents"
    publication_date: str | None = None
    snippet: str | None = None
    relevance_score: float = 0.0
    matched_features: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)


class PatentSearchResult(BaseModel):
    """Search queries and up to five genuine, ranked patent candidates."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    queries: list[str] = Field(default_factory=list)
    results: list[PatentResult] = Field(default_factory=list, max_length=5)
    warnings: list[str] = Field(default_factory=list)
