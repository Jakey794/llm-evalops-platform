import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TestCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    external_id: str
    input: dict[str, Any] = Field(validation_alias="input_json")
    expected_output: dict[str, Any] = Field(validation_alias="expected_output_json")
    required_citations: list[str]
    tags: list[str]
    difficulty: str
    workflow_type: str
    metadata: dict[str, Any] = Field(validation_alias="metadata_json")
    created_at: datetime
