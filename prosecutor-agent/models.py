from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ProsecutorRequest(BaseModel):

    product: Dict[str, Any] = Field(
        ...,
        description="Product information from Agent 1"
    )

    patents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Patent information retrieved by the patent search layer"
    )


class ClaimElement(BaseModel):

    claim_element: str

    product_feature: str

    overlap: bool

    risk: str

    reason: str


class ProsecutorOutput(BaseModel):

    agent: str = "prosecutor"

    risk_level: str

    summary: str

    claim_elements: List[ClaimElement] = Field(
        default_factory=list
    )

    patents_analyzed: List[Any] = Field(
        default_factory=list
    )

    disclaimer: str