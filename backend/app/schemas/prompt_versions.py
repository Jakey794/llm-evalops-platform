import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PromptVersionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    workflow_type: str = Field(min_length=1, max_length=100)
    template: str = Field(min_length=1)
    version_label: str = Field(min_length=1, max_length=100)


class PromptVersionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    workflow_type: str
    version_label: str
    created_at: datetime


class PromptVersionResponse(PromptVersionListItem):
    template: str
