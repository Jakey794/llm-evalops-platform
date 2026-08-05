import pytest
from pydantic import ValidationError

from app.schemas import LLMJudgeOutput


def _valid_payload() -> dict[str, object]:
    return {
        "score": 0.75,
        "passed": True,
        "reason": "The response satisfies most rubric criteria.",
        "failure_modes": ["missing_citation"],
        "rubric_scores": {"correctness": 1.0, "groundedness": 0.5},
    }


def test_llm_judge_output_accepts_valid_output_and_boundaries() -> None:
    output = LLMJudgeOutput.model_validate(_valid_payload())
    lower = LLMJudgeOutput.model_validate({**_valid_payload(), "score": 0.0})
    upper = LLMJudgeOutput.model_validate({**_valid_payload(), "score": 1.0})

    assert output.rubric_scores == {"correctness": 1.0, "groundedness": 0.5}
    assert lower.score == 0.0
    assert upper.score == 1.0


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_llm_judge_output_rejects_out_of_range_score(score: float) -> None:
    with pytest.raises(ValidationError):
        LLMJudgeOutput.model_validate({**_valid_payload(), "score": score})


@pytest.mark.parametrize("rubric_score", [-0.01, 1.01])
def test_llm_judge_output_rejects_out_of_range_rubric_score(rubric_score: float) -> None:
    with pytest.raises(ValidationError):
        LLMJudgeOutput.model_validate(
            {**_valid_payload(), "rubric_scores": {"correctness": rubric_score}}
        )


def test_llm_judge_output_requires_all_fields_and_forbids_extras() -> None:
    missing_reason = _valid_payload()
    missing_reason.pop("reason")

    with pytest.raises(ValidationError):
        LLMJudgeOutput.model_validate(missing_reason)
    with pytest.raises(ValidationError):
        LLMJudgeOutput.model_validate({**_valid_payload(), "unexpected": True})
