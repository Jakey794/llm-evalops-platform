from typing import Any

import pytest

from app.graders import GraderInput, GraderResult, JsonSchemaGrader


def grade(
    *,
    model_output: dict[str, Any] | str | None,
    config: dict[str, Any] | None = None,
    parsed_output: dict[str, Any] | None = None,
    nested_config: bool = False,
) -> GraderResult:
    grader_config = {"json_schema": config or {}} if nested_config else config or {}
    return JsonSchemaGrader().grade(
        GraderInput(
            test_case_id="case-1",
            workflow_type="incident_triage",
            input_data={"title": "Database unavailable"},
            expected_output=None,
            model_output=model_output,
            parsed_output=parsed_output,
            grader_config=grader_config,
        )
    )


def schema_config(**overrides: Any) -> dict[str, Any]:
    config: dict[str, Any] = {
        "required_fields": ["severity", "category"],
        "field_types": {"severity": "string", "category": "string"},
        "enums": {"severity": ["sev-1", "sev-2", "sev-3"]},
    }
    config.update(overrides)
    return config


def test_valid_object_passes() -> None:
    result = grade(
        model_output={"severity": "sev-1", "category": "database"},
        config=schema_config(),
        nested_config=True,
    )

    assert result.score == 1.0
    assert result.passed is True
    assert result.failure_modes == []


def test_invalid_json_fails() -> None:
    result = grade(model_output="{invalid", config=schema_config())

    assert result.score == 0.0
    assert result.passed is False
    assert result.failure_modes == ["invalid_json"]


def test_missing_required_field_receives_partial_credit() -> None:
    result = grade(
        model_output={"severity": "sev-1"},
        config=schema_config(enums={}),
    )

    assert result.score == pytest.approx(0.6875)
    assert 0.0 < result.score < 1.0
    assert result.passed is False
    assert result.failure_modes == ["missing_required_field"]


def test_wrong_type_receives_partial_credit() -> None:
    result = grade(
        model_output={"severity": 1, "category": "database"},
        config=schema_config(enums={}),
    )

    assert result.score == pytest.approx(0.8125)
    assert result.passed is False
    assert result.failure_modes == ["wrong_type"]


def test_invalid_enum_receives_partial_credit() -> None:
    result = grade(
        model_output={"severity": "sev-9", "category": "database"},
        config=schema_config(),
    )

    assert result.score == pytest.approx(0.8)
    assert result.passed is False
    assert result.failure_modes == ["invalid_enum"]


def test_extra_field_is_allowed_by_default() -> None:
    result = grade(
        model_output={
            "severity": "sev-1",
            "category": "database",
            "explanation": "Connection pool exhausted",
        },
        config=schema_config(),
    )

    assert result.score == 1.0
    assert result.passed is True
    assert result.failure_modes == []


def test_disallowed_extra_field_reduces_score() -> None:
    result = grade(
        model_output={
            "severity": "sev-1",
            "category": "database",
            "explanation": "Connection pool exhausted",
        },
        config=schema_config(allow_extra_fields=False),
    )

    assert result.score == pytest.approx(2 / 3)
    assert result.passed is False
    assert result.failure_modes == ["unexpected_extra_field"]
    assert "explanation" in result.feedback


def test_no_config_returns_pass_with_explanation() -> None:
    result = grade(model_output="not json")

    assert result.score == 1.0
    assert result.passed is True
    assert result.failure_modes == []
    assert result.feedback == (
        "No JSON schema constraints configured; structured output passed by default."
    )


def test_parsed_output_takes_precedence_over_model_output() -> None:
    result = grade(
        model_output="{invalid",
        parsed_output={"severity": "sev-1", "category": "database"},
        config=schema_config(),
    )

    assert result.score == 1.0
    assert result.passed is True


def test_empty_required_value_is_reported() -> None:
    result = grade(
        model_output={"severity": "   ", "category": "database"},
        config=schema_config(enums={}),
    )

    assert 0.0 < result.score < 1.0
    assert result.failure_modes == ["empty_required_value"]


@pytest.mark.parametrize(
    ("type_name", "value"),
    [
        ("string", "value"),
        ("number", 1.5),
        ("integer", 1),
        ("boolean", True),
        ("array", []),
        ("object", {}),
        ("null", None),
    ],
)
def test_supported_field_types(type_name: str, value: Any) -> None:
    result = grade(
        model_output={"value": value},
        config={"field_types": {"value": type_name}},
    )

    assert result.score == 1.0
    assert result.passed is True


@pytest.mark.parametrize("type_name", ["number", "integer"])
def test_boolean_is_not_accepted_as_numeric_type(type_name: str) -> None:
    result = grade(
        model_output={"value": True},
        config={"field_types": {"value": type_name}},
    )

    assert result.score == 0.0
    assert result.failure_modes == ["wrong_type"]


def test_threshold_can_allow_partial_credit_to_pass() -> None:
    result = grade(
        model_output={"severity": "sev-9", "category": "database"},
        config=schema_config(threshold=0.8),
    )

    assert result.score == pytest.approx(0.8)
    assert result.passed is True
