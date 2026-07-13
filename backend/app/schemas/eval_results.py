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
    score: float = Field(default=0.0, ge=0, le=1)
    passed: bool = False
    grader_feedback: str = ""
    failure_modes: list[str] = Field(default_factory=list)
    grader_breakdown: dict[str, Any] = Field(default_factory=dict)


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
    score: float
    passed: bool
    grader_feedback: str
    failure_modes: list[str]
    grader_breakdown: dict[str, Any]
    created_at: datetime


class GraderResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    grader_name: str
    grader_type: str
    score: float | None
    passed: bool | None
    feedback: str | None
    failure_modes: list[str]
    rubric_scores: dict[str, float]
    raw_output: dict[str, Any] | None
    error: str | None
    created_at: datetime


class EvalResultResponse(EvalResultListItem):
    raw_response: dict[str, Any] | None
    grader_results: list[GraderResultResponse] = Field(default_factory=list)


class GraderErrorResponse(BaseModel):
    grader_name: str
    error: str


class FailedExampleResponse(BaseModel):
    id: uuid.UUID
    eval_run_id: uuid.UUID
    test_case_id: uuid.UUID
    workflow_type: str
    difficulty: str
    tags: list[str]
    input_json: dict[str, Any]
    expected_output_json: dict[str, Any]
    model_output: str | None
    final_score: float
    passed: bool
    deterministic_grader_scores: dict[str, float]
    llm_judge_score: float | None
    judge_reason: str | None
    failure_modes: list[str]
    rubric_scores: dict[str, float]
    grader_errors: list[GraderErrorResponse]
    grader_results: list[GraderResultResponse]
    created_at: datetime
