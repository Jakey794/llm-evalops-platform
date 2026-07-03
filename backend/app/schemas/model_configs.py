import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ModelProvider


class ModelConfigCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    provider: ModelProvider
    model_name: str = Field(min_length=1, max_length=255)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_output_tokens: int = Field(gt=0)
    response_format: dict[str, Any] | None = None


class ModelConfigListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: ModelProvider
    model_name: str
    temperature: float | None
    max_output_tokens: int
    created_at: datetime


class ModelConfigResponse(ModelConfigListItem):
    response_format: dict[str, Any] | None
