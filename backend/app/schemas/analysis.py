from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalysisCreate(BaseModel):
    product_id: UUID


class AnalysisRead(BaseModel):
    id: UUID
    product_id: UUID
    status: str
    created_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisError(BaseModel):
    stage: str | None = None
    message: str | None = None


class AnalysisDetail(AnalysisRead):
    """The analysis plus every stage's output, assembled from ``agent_runs``."""

    feature_extraction: dict[str, Any] | None = None
    patent_search: dict[str, Any] | None = None
    patents: list[dict[str, Any]] = []
    prosecutor: dict[str, Any] | None = None
    defender: dict[str, Any] | None = None
    design: dict[str, Any] | None = None
    risk_matrix: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    images: list[dict[str, Any]] = []
    errors: list[AnalysisError] = []
