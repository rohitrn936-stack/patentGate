from datetime import datetime
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
