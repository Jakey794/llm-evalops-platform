from typing import Any

import pytest

from app.graders import GraderInput, GraderResult, TextSimilarityGrader


def grade(
    *,
    expected_output: dict[str, Any] | str | None,
    model_output: dict[str, Any] | str | None,
    config: dict[str, Any] | None = None,
    parsed_output: dict[str, Any] | None = None,
    nested_config: bool = False,
) -> GraderResult:
    grader_config = {"text_similarity": config or {}} if nested_config else config or {}
    return TextSimilarityGrader().grade(
        GraderInput(
            test_case_id="case-1",
            workflow_type="incident_triage",
            input_data={"title": "Database unavailable"},
            expected_output=expected_output,
            model_output=model_output,
            parsed_output=parsed_output,
            grader_config=grader_config,
        )
    )


def test_exact_text_passes() -> None:
    result = grade(
        expected_output="Restart the database connection pool.",
        model_output="Restart the database connection pool.",
        nested_config=True,
    )

    assert result.score == 1.0
    assert result.passed is True
    assert result.failure_modes == []


def test_case_and_whitespace_are_normalized() -> None:
    result = grade(
        expected_output="Restart the DATABASE connection pool!",
        model_output="  restart   the database\nconnection pool ",
    )

    assert result.score == 1.0
    assert result.passed is True


def test_answer_contains_all_phrases_passes() -> None:
    result = grade(
        expected_output={"answer_contains": ["database", "restart connection pool"]},
        model_output="Restart connection pool for the database immediately.",
    )

    assert result.score == 1.0
    assert result.passed is True
    assert result.metadata["contains_score"] == 1.0


def test_answer_contains_partial_score() -> None:
    result = grade(
        expected_output=None,
        model_output="The database is unavailable.",
        config={
            "answer_contains": ["database", "requires immediate customer notification"],
            "threshold": 0.5,
        },
    )

    assert result.score == 0.5
    assert result.passed is True
    assert result.failure_modes == ["missing_required_phrase"]


def test_missing_phrase_fails() -> None:
    result = grade(
        expected_output="Database outage requires customer notification.",
        model_output="The database is unavailable.",
        config={"answer_contains": ["database", "customer notification"]},
    )

    assert result.score < 0.75
    assert result.passed is False
    assert result.failure_modes == ["missing_required_phrase", "low_text_similarity"]


def test_obviously_wrong_answer_fails() -> None:
    result = grade(
        expected_output="Restart the database connection pool.",
        model_output="The weather is sunny today.",
    )

    assert result.score < 0.75
    assert result.passed is False
    assert result.failure_modes == ["low_text_similarity"]


def test_similarity_ratio_is_pinned_for_known_inputs() -> None:
    result = grade(
        expected_output="Restart the database connection pool now.",
        model_output="Restart database connection pool immediately.",
    )

    assert result.score == pytest.approx(0.7857142857142857)
    assert result.passed is True
    assert result.failure_modes == []


def test_expected_and_actual_dot_path_extraction() -> None:
    result = grade(
        expected_output={"resolution": {"summary": "Restart database"}},
        model_output={"result": {"message": "wrong"}},
        parsed_output={"result": {"message": "Restart database"}},
        config={
            "expected_field": "resolution.summary",
            "actual_field": "result.message",
        },
    )

    assert result.score == 1.0
    assert result.passed is True


def test_missing_expected_text_fails_cleanly() -> None:
    result = grade(expected_output={}, model_output="some answer")

    assert result.score == 0.0
    assert result.failure_modes == ["missing_expected_text"]


def test_missing_actual_text_fails_cleanly() -> None:
    result = grade(expected_output="some answer", model_output=None)

    assert result.score == 0.0
    assert result.failure_modes == ["missing_actual_text"]


@pytest.mark.parametrize(
    "model_output",
    [
        {"answer": "Restart database"},
        None,
    ],
)
def test_actual_field_missing_fails_cleanly(
    model_output: dict[str, Any] | None,
) -> None:
    result = grade(
        expected_output="Restart database",
        model_output=model_output,
        config={"actual_field": "result.message"},
    )

    assert result.failure_modes == ["missing_actual_text"]
