from typing import Any

import pytest

from app.graders import ExactMatchGrader, GraderInput


def grade(
    *,
    expected_output: dict[str, Any] | str | None,
    model_output: dict[str, Any] | str | None,
    exact_fields: list[str] | None = None,
    parsed_output: dict[str, Any] | None = None,
    config_overrides: dict[str, Any] | None = None,
    nested_config: bool = False,
):
    config: dict[str, Any] = dict(config_overrides or {})
    if exact_fields is not None:
        config["exact_fields"] = exact_fields
    grader_config = {"exact_match": config} if nested_config else config

    return ExactMatchGrader().grade(
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


def test_perfect_match_prefers_parsed_output_and_nested_config() -> None:
    result = grade(
        expected_output={"severity": "sev-1", "category": "database"},
        model_output={"severity": "wrong", "category": "wrong"},
        parsed_output={"severity": "sev-1", "category": "database"},
        exact_fields=["severity", "category"],
        nested_config=True,
    )

    assert result.score == 1.0
    assert result.passed is True
    assert result.failure_modes == []
    assert result.feedback == "Matched 2/2 exact fields."


def test_case_insensitive_match() -> None:
    result = grade(
        expected_output={"category": "Database"},
        model_output={"category": "database"},
        exact_fields=["category"],
    )

    assert result.score == 1.0
    assert result.passed is True


def test_whitespace_normalized_match() -> None:
    result = grade(
        expected_output={"summary": "Database   is\ndown"},
        model_output={"summary": "Database is down"},
        exact_fields=["summary"],
    )

    assert result.score == 1.0
    assert result.passed is True


def test_wrong_field_reports_mismatch() -> None:
    result = grade(
        expected_output={"severity": "sev-1", "category": "database"},
        model_output={"severity": "sev-2", "category": "database"},
        exact_fields=["severity", "category"],
    )

    assert result.score == 0.5
    assert result.passed is False
    assert result.failure_modes == ["field_mismatch"]
    assert result.feedback == (
        "Matched 1/2 exact fields. severity expected 'sev-1' but got 'sev-2'."
    )


def test_missing_actual_field() -> None:
    result = grade(
        expected_output={"severity": "sev-1"},
        model_output={},
        exact_fields=["severity"],
    )

    assert result.score == 0.0
    assert result.passed is False
    assert result.failure_modes == ["missing_actual_field"]
    assert "severity is missing from actual output." in result.feedback


def test_missing_expected_field() -> None:
    result = grade(
        expected_output={},
        model_output={"severity": "sev-1"},
        exact_fields=["severity"],
    )

    assert result.score == 0.0
    assert result.passed is False
    assert result.failure_modes == ["missing_expected_field"]
    assert "severity is missing from expected output." in result.feedback


def test_nested_dot_path_field() -> None:
    result = grade(
        expected_output={"root_cause": {"category": "database"}},
        model_output={"root_cause": {"category": "database"}},
        exact_fields=["root_cause.category"],
    )

    assert result.score == 1.0
    assert result.passed is True


def test_json_string_model_output() -> None:
    result = grade(
        expected_output='{"severity":"sev-1"}',
        model_output='{"severity":"sev-1"}',
        exact_fields=["severity"],
    )

    assert result.score == 1.0
    assert result.passed is True


def test_no_configured_exact_fields_passes_by_default() -> None:
    result = grade(
        expected_output=None,
        model_output="not json",
    )

    assert result.score == 1.0
    assert result.passed is True
    assert result.failure_modes == []
    assert result.feedback == "No exact fields configured; exact match passed by default."


def test_threshold_can_allow_partial_match() -> None:
    result = grade(
        expected_output={"severity": "sev-1", "category": "database"},
        model_output={"severity": "sev-2", "category": "database"},
        exact_fields=["severity", "category"],
        config_overrides={"threshold": 0.5},
    )

    assert result.score == 0.5
    assert result.passed is True


@pytest.mark.parametrize("model_output", [None, "not json", "[]"])
def test_unusable_model_output_is_treated_as_missing(model_output: str | None) -> None:
    result = grade(
        expected_output={"severity": "sev-1"},
        model_output=model_output,
        exact_fields=["severity"],
    )

    assert result.failure_modes == ["missing_actual_field"]
