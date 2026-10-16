from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_MAX_DESCRIPTION = 20_000


def _safe_image_url(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value
    if value.startswith("data:image/"):
        return value
    raise ValueError("image_url must be an http(s) URL or a data:image/ URL")


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=_MAX_DESCRIPTION)
    image_url: str | None = Field(default=None, max_length=2048)

    @field_validator("name", "description")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("image_url")
    @classmethod
    def _validate_image_url(cls, value: str | None) -> str | None:
        return _safe_image_url(value)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=_MAX_DESCRIPTION)
    image_url: str | None = Field(default=None, max_length=2048)

    @field_validator("image_url")
    @classmethod
    def _validate_image_url(cls, value: str | None) -> str | None:
        return _safe_image_url(value)


class ProductRead(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str
    image_url: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
