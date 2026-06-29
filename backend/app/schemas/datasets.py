import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.jsonl_importer import JsonlImportError


class DatasetImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    workflow_type: str = Field(min_length=1, max_length=100)
    source_filename: str | None = Field(default=None, max_length=255)
    jsonl_content: str

    @field_validator("name", "workflow_type")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("description", "source_filename")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class DatasetImportResponse(BaseModel):
    dataset_id: uuid.UUID | None
    imported_count: int
    rejected_count: int
    errors: list[JsonlImportError]


class DatasetListItem(BaseModel):
    id: uuid.UUID
    name: str
    workflow_type: str
    source_filename: str | None
    created_at: datetime
    test_case_count: int


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    workflow_type: str
    source_filename: str | None
    created_at: datetime


class DatasetDetailResponse(DatasetResponse):
    test_case_count: int
