import pytest
from pydantic import ValidationError

from app.graders import BaseGrader, GraderInput, GraderResult, clamp_score


def make_grader_input() -> GraderInput:
    return GraderInput(
        test_case_id="case-1",
        workflow_type="support_classification",
        input_data={"ticket": "I need help with an invoice."},
        expected_output={"category": "billing"},
        model_output='{"category":"billing"}',
        parsed_output={"category": "billing"},
    )


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_grader_result_rejects_score_outside_unit_interval(score: float) -> None:
    with pytest.raises(ValidationError):
        GraderResult(
            grader_name="fake",
            score=score,
            passed=False,
            feedback="Invalid score.",
        )


def test_grader_result_accepts_valid_output() -> None:
    result = GraderResult(
        grader_name="exact_match",
        score=1.0,
        passed=True,
        feedback="Outputs match.",
        metadata={"matched": True},
    )

    assert result.score == 1.0
    assert result.passed is True
    assert result.failure_modes == []


def test_fake_grader_returns_valid_result() -> None:
    class FakeGrader(BaseGrader):
        name = "fake"

        def grade(self, input: GraderInput) -> GraderResult:
            return GraderResult(
                grader_name=self.name,
                score=1.0 if input.parsed_output == input.expected_output else 0.0,
                passed=input.parsed_output == input.expected_output,
                feedback="Compared parsed and expected output.",
            )

    result = FakeGrader().grade(make_grader_input())

    assert result == GraderResult(
        grader_name="fake",
        score=1.0,
        passed=True,
        feedback="Compared parsed and expected output.",
    )


def test_mutable_defaults_are_not_shared() -> None:
    first_input = make_grader_input()
    second_input = make_grader_input()
    first_result = GraderResult(
        grader_name="fake",
        score=0.0,
        passed=False,
        feedback="No match.",
    )
    second_result = GraderResult(
        grader_name="fake",
        score=0.0,
        passed=False,
        feedback="No match.",
    )

    first_input.tags.append("regression")
    first_input.grader_config["case_sensitive"] = True
    first_result.failure_modes.append("mismatch")
    first_result.metadata["expected"] = "billing"

    assert second_input.tags == []
    assert second_input.grader_config == {}
    assert second_result.failure_modes == []
    assert second_result.metadata == {}


@pytest.mark.parametrize(
    ("value", "expected"),
    [(-1.0, 0.0), (0.25, 0.25), (2.0, 1.0)],
)
def test_clamp_score(value: float, expected: float) -> None:
    assert clamp_score(value) == expected
