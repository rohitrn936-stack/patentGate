from pydantic import BaseModel, Field


class Agent1Request(BaseModel):
    input: str = Field(..., min_length=1, description="User's product description")


class Agent1Response(BaseModel):
    success: bool
    result: dict | None = None
    error: str | None = None