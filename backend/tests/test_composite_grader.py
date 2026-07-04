from typing import Any

import pytest

from app.graders import CompositeGrader, GraderInput, GraderResult


def grade(
    *,
    expected_output: dict[str, Any] | str | None,
    model_output: dict[str, Any] | str | None,
    grader_config: dict[str, Any],
    parsed_output: dict[str, Any] | None = None,
) -> GraderResult:
    return CompositeGrader().grade(
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


def component_config(
    graders: list[dict[str, Any]],
    *,
    pass_threshold: float = 0.8,
    actual_severity: str = "sev-2",
    actual_summary: str = "Restart database",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    expected = {"severity": "sev-1", "summary": "Restart database"}
    actual = {"severity": actual_severity, "summary": actual_summary}
    config = {
        "composite": {"graders": graders, "pass_threshold": pass_threshold},
        "json_schema": {
            "required_fields": ["severity", "summary"],
            "field_types": {"severity": "string", "summary": "string"},
        },
        "exact_match": {"exact_fields": ["severity"]},
        "text_similarity": {
            "expected_field": "summary",
            "actual_field": "summary",
        },
    }
    return expected, actual, config


def test_weighted_average_is_correct() -> None:
    expected, actual, config = component_config(
        [
            {"name": "json_schema", "weight": 0.35},
            {"name": "exact_match", "weight": 0.40},
            {"name": "text_similarity", "weight": 0.25},
        ]
    )

    result = grade(
        expected_output=expected,
        model_output=actual,
        parsed_output=actual,
        grader_config=config,
    )

    assert result.score == pytest.approx(0.6)
    assert result.metadata["breakdown"] == {
        "json_schema": 1.0,
        "exact_match": 0.0,
        "text_similarity": 1.0,
    }
    assert len(result.metadata["grader_results"]) == 3


def test_weights_are_normalized() -> None:
    expected, actual, config = component_config(
        [
            {"name": "exact_match", "weight": 2},
            {"name": "text_similarity", "weight": 1},
        ]
    )

    result = grade(
        expected_output=expected,
        model_output=actual,
        parsed_output=actual,
        grader_config=config,
    )

    assert result.score == pytest.approx(1 / 3)
    assert result.metadata["weights"] == pytest.approx(
        {"exact_match": 2 / 3, "text_similarity": 1 / 3}
    )


def test_pass_threshold_is_applied() -> None:
    expected, actual, config = component_config(
        [
            {"name": "exact_match", "weight": 1},
            {"name": "text_similarity", "weight": 1},
        ],
        pass_threshold=0.5,
    )

    result = grade(
        expected_output=expected,
        model_output=actual,
        parsed_output=actual,
        grader_config=config,
    )

    assert result.score == 0.5
    assert result.passed is True
    assert result.metadata["pass_threshold"] == 0.5


def test_failure_modes_are_aggregated_uniquely() -> None:
    expected, actual, config = component_config(
        [
            {"name": "json_schema", "weight": 1},
            {"name": "exact_match", "weight": 1},
            {"name": "text_similarity", "weight": 1},
        ],
        actual_severity="sev-9",
        actual_summary="Weather is sunny",
    )
    config["json_schema"]["enums"] = {"severity": ["sev-1", "sev-2"]}

    result = grade(
        expected_output=expected,
        model_output=actual,
        parsed_output=actual,
        grader_config=config,
    )

    assert result.failure_modes == ["invalid_enum", "field_mismatch", "low_text_similarity"]


def test_one_grader_can_fail_while_composite_passes() -> None:
    expected, actual, config = component_config(
        [
            {"name": "exact_match", "weight": 0.1},
            {"name": "json_schema", "weight": 0.45},
            {"name": "text_similarity", "weight": 0.45},
        ]
    )

    result = grade(
        expected_output=expected,
        model_output=actual,
        parsed_output=actual,
        grader_config=config,
    )

    assert result.score == pytest.approx(0.9)
    assert result.passed is True
    assert "field_mismatch" in result.failure_modes


def test_zero_weight_grader_contributes_nothing() -> None:
    expected, actual, config = component_config(
        [
            {"name": "json_schema", "weight": 0},
            {"name": "exact_match", "weight": 0.5},
            {"name": "text_similarity", "weight": 0.5},
        ]
    )

    result = grade(
        expected_output=expected,
        model_output=actual,
        parsed_output=actual,
        grader_config=config,
    )

    assert result.score == pytest.approx(0.5)
    assert result.metadata["weights"] == pytest.approx(
        {"json_schema": 0.0, "exact_match": 0.5, "text_similarity": 0.5}
    )
    assert result.metadata["breakdown"]["json_schema"] == 1.0


@pytest.mark.parametrize(
    ("grader_spec", "expected_feedback"),
    [
        ({"name": "does_not_exist", "weight": 1}, "Unknown grader 'does_not_exist'."),
        ({"weight": 1}, "Grader configuration is missing a valid name."),
    ],
)
def test_unknown_or_missing_grader_is_handled_clearly(
    grader_spec: dict[str, Any],
    expected_feedback: str,
) -> None:
    result = grade(
        expected_output="expected",
        model_output="actual",
        grader_config={"composite": {"graders": [grader_spec]}},
    )

    assert result.score == 0.0
    assert result.passed is False
    assert result.failure_modes == ["unknown_grader"]
    assert expected_feedback in result.feedback
    assert result.metadata["grader_results"][0]["feedback"] == expected_feedback


def test_no_graders_configured_returns_useful_failed_result() -> None:
    result = grade(
        expected_output=None,
        model_output=None,
        grader_config={"composite": {"graders": []}},
    )

    assert result.score == 0.0
    assert result.passed is False
    assert result.failure_modes == ["no_graders_configured"]
    assert result.metadata["breakdown"] == {}
    assert result.metadata["grader_results"] == []
    assert "No component graders" in result.feedback


def test_default_grader_is_inferred_from_flat_config() -> None:
    result = grade(
        expected_output={"severity": "sev-1"},
        model_output={"severity": "sev-1"},
        grader_config={"exact_fields": ["severity"]},
    )

    assert result.score == 1.0
    assert result.passed is True
    assert result.metadata["breakdown"] == {"exact_match": 1.0}
    assert result.metadata["weights"] == {"exact_match": 1.0}
