import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvalResultCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eval_run_id: uuid.UUID
    test_case_id: uuid.UUID
    model_output: str | None = None
    parsed_output: dict[str, Any] | list[Any] | None = None
    raw_response: dict[str, Any] | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: Decimal | None = Field(default=None, ge=0)
    error: str | None = None


class EvalResultListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    eval_run_id: uuid.UUID
    test_case_id: uuid.UUID
    model_output: str | None
    parsed_output: dict[str, Any] | list[Any] | None
    latency_ms: float | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: Decimal | None
    error: str | None
    created_at: datetime


class EvalResultResponse(EvalResultListItem):
    raw_response: dict[str, Any] | None
