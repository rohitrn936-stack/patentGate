from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskItem(BaseModel):
    """
    Risk assessment for one potentially exposed claim element.
    """

    claim_element: str = Field(
        ...,
        min_length=1,
        description="Claim element being assessed",
    )

    risk_level: RiskLevel

    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Risk score from 0 to 100",
    )

    reason: str = Field(
        ...,
        min_length=1,
        description="Explanation for the assigned risk",
    )

    supporting_patents: List[str] = Field(
        default_factory=list,
        description="Patent identifiers supporting the assessment",
    )

    prior_art_overlap: Optional[str] = Field(
        default=None,
        description="Description of overlap with prior art",
    )

    distinction: Optional[str] = Field(
        default=None,
        description="Relevant distinction identified by Agent 3",
    )

    recommended_action: Optional[str] = Field(
        default=None,
        description="Suggested engineering or claim strategy",
    )


class RiskMatrixRequest(BaseModel):
    """
    Input to the Risk Matrix.

    This combines information from Agent 2, Agent 3,
    and Agent 4.
    """

    product_description: str = Field(
        ...,
        min_length=1,
    )

    claim_elements: List[str] = Field(
        default_factory=list,
        description="Claim elements identified by Agent 2",
    )

    risky_elements: List[str] = Field(
        default_factory=list,
        description="Elements identified as potentially risky",
    )

    prior_art_findings: List[dict] = Field(
        default_factory=list,
        description="Findings returned by Agent 3",
    )

    redesign_options: List[dict] = Field(
        default_factory=list,
        description="Engineering alternatives from Agent 4",
    )


class RiskMatrixResponse(BaseModel):
    """
    Complete Risk Matrix response.
    """

    status: str

    overall_score: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
    )

    overall_risk: Optional[RiskLevel] = None

    risks: List[RiskItem] = Field(
        default_factory=list,
    )

    error: Optional[str] = None