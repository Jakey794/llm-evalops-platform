from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class GraderInput(BaseModel):
    test_case_id: str
    workflow_type: str
    input_data: dict[str, Any] | str
    expected_output: dict[str, Any] | str | None
    model_output: dict[str, Any] | str | None
    parsed_output: dict[str, Any] | None = None
    grader_config: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    difficulty: str | None = None


class GraderResult(BaseModel):
    grader_name: str
    score: float = Field(ge=0, le=1)
    passed: bool
    feedback: str
    failure_modes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseGrader(ABC):
    name: ClassVar[str]

    @abstractmethod
    def grade(self, input: GraderInput) -> GraderResult:
        """Grade one model output deterministically."""


def clamp_score(value: float) -> float:
    return max(0.0, min(1.0, value))
