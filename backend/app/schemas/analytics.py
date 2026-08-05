from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BreakdownBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    total_count: int = Field(ge=0)
    passed_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    pass_rate: float | None = None
    avg_score: float | None = None
    avg_latency_ms: float | None = None
    total_cost_usd: float = 0.0


class RunAnalyticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eval_run_id: UUID
    by_tag: list[BreakdownBucket]
    by_difficulty: list[BreakdownBucket]
    by_workflow: list[BreakdownBucket]
    incomplete_cases: int = Field(ge=0)
    has_partial_metrics: bool


class CompareRunPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    label: str
    status: str
    dataset_name: str | None = None
    prompt_name: str | None = None
    prompt_version_label: str | None = None
    model_name: str | None = None
    pass_rate: float | None = None
    avg_score: float | None = None
    total_cost_usd: float = 0.0
    avg_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    failed_count: int = 0
    total_count: int = 0


class CompareRunsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runs: list[CompareRunPoint]
    cost_quality: list[dict[str, float | str | None]]
    latency_quality: list[dict[str, float | str | None]]


class DashboardOverviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_count: int = Field(ge=0)
    completed_run_count: int = Field(ge=0)
    pass_rate: float | None = None
    avg_score: float | None = None
    total_cost_usd: float = 0.0
    avg_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    has_partial_metrics: bool
    recent_runs: list[CompareRunPoint]
