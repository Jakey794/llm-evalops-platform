from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

type UnitInterval = Annotated[float, Field(ge=0.0, le=1.0)]


class LLMJudgeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: UnitInterval
    passed: bool
    reason: str
    failure_modes: list[str]
    rubric_scores: dict[str, UnitInterval]
