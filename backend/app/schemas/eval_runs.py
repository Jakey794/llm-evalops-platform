import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import EvalRunStatus


class EvalRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: uuid.UUID
    prompt_version_id: uuid.UUID
    model_config_id: uuid.UUID


class EvalRunListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    prompt_version_id: uuid.UUID
    model_config_id: uuid.UUID
    status: EvalRunStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    total_cases: int
    completed_cases: int
    pass_rate: float | None
    avg_score: float | None
    total_cost_usd: Decimal
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    error_count: int
    failed_count: int
    total_count: int
    model_name: str | None = None
    dataset_name: str | None = None
    prompt_name: str | None = None
    prompt_version_label: str | None = None


class EvalRunResponse(EvalRunListItem):
    pass
