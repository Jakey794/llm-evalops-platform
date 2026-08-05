import json
from typing import Any

from app.graders.base import BaseGrader, GraderInput, GraderResult, clamp_score

_SECTION_WEIGHTS = {
    "required_fields": 0.5,
    "field_types": 0.3,
    "enums": 0.2,
}


class JsonSchemaGrader(BaseGrader):
    name = "json_schema"

    def grade(self, input: GraderInput) -> GraderResult:
        config = _get_config(input.grader_config)
        required_fields = _get_string_list(config.get("required_fields"))
        field_types = _get_string_mapping(config.get("field_types"))
        enums = _get_enums(config.get("enums"))
        allow_extra_fields = bool(config.get("allow_extra_fields", True))

        if not required_fields and not field_types and not enums and allow_extra_fields:
            return GraderResult(
                grader_name=self.name,
                score=1.0,
                passed=True,
                feedback=(
                    "No JSON schema constraints configured; structured output passed by default."
                ),
            )

        output = _get_output(input)
        if output is None:
            return GraderResult(
                grader_name=self.name,
                score=0.0,
                passed=False,
                feedback="Model output is not a valid JSON object.",
                failure_modes=["invalid_json"],
            )

        failure_modes: list[str] = []
        feedback_parts: list[str] = []
        sections: list[tuple[float, float]] = []

        if required_fields:
            valid_required = 0
            for field in required_fields:
                if field not in output:
                    _add_failure_mode(failure_modes, "missing_required_field")
                elif _is_empty_required_value(output[field]):
                    _add_failure_mode(failure_modes, "empty_required_value")
                else:
                    valid_required += 1
            sections.append(
                (_SECTION_WEIGHTS["required_fields"], valid_required / len(required_fields))
            )
            feedback_parts.append(
                f"Required fields: {valid_required}/{len(required_fields)} valid."
            )

        if field_types:
            present_types = {
                field: type_name for field, type_name in field_types.items() if field in output
            }
            correct_types = sum(
                _matches_type(output[field], type_name)
                for field, type_name in present_types.items()
            )
            for field, type_name in present_types.items():
                if not _matches_type(output[field], type_name):
                    _add_failure_mode(failure_modes, "wrong_type")
            type_score = correct_types / len(present_types) if present_types else 1.0
            sections.append((_SECTION_WEIGHTS["field_types"], type_score))
            feedback_parts.append(
                f"Field types: {correct_types}/{len(present_types)} present fields valid."
            )

        if enums:
            present_enums = {
                field: allowed_values for field, allowed_values in enums.items() if field in output
            }
            correct_enums = sum(
                output[field] in allowed_values for field, allowed_values in present_enums.items()
            )
            for field, allowed_values in present_enums.items():
                if output[field] not in allowed_values:
                    _add_failure_mode(failure_modes, "invalid_enum")
            enum_score = correct_enums / len(present_enums) if present_enums else 1.0
            sections.append((_SECTION_WEIGHTS["enums"], enum_score))
            feedback_parts.append(
                f"Enum values: {correct_enums}/{len(present_enums)} present fields valid."
            )

        score = _weighted_score(sections)
        if not allow_extra_fields:
            configured_fields = set(required_fields) | set(field_types) | set(enums)
            extra_fields = sorted(set(output) - configured_fields)
            if extra_fields:
                _add_failure_mode(failure_modes, "unexpected_extra_field")
                score *= (len(output) - len(extra_fields)) / len(output)
                feedback_parts.append(f"Unexpected extra fields: {', '.join(extra_fields)}.")

        score = clamp_score(score)
        threshold = _get_threshold(config)
        feedback = " ".join(feedback_parts) or "JSON object satisfied the configured constraints."
        return GraderResult(
            grader_name=self.name,
            score=score,
            passed=score >= threshold,
            feedback=feedback,
            failure_modes=failure_modes,
        )


def _get_config(grader_config: dict[str, Any]) -> dict[str, Any]:
    config = grader_config.get("json_schema", grader_config)
    return config if isinstance(config, dict) else {}


def _get_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _get_string_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        field: type_name
        for field, type_name in value.items()
        if isinstance(field, str) and isinstance(type_name, str)
    }


def _get_enums(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    return {
        field: allowed_values
        for field, allowed_values in value.items()
        if isinstance(field, str)
        and isinstance(allowed_values, list)
        and all(isinstance(item, str) for item in allowed_values)
    }


def _get_output(input: GraderInput) -> dict[str, Any] | None:
    if input.parsed_output is not None:
        return input.parsed_output
    if isinstance(input.model_output, dict):
        return input.model_output
    if not isinstance(input.model_output, str):
        return None

    try:
        decoded = json.loads(input.model_output)
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def _is_empty_required_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return not value
    return False


def _matches_type(value: Any, type_name: str) -> bool:
    match type_name:
        case "string":
            return isinstance(value, str)
        case "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        case "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        case "boolean":
            return isinstance(value, bool)
        case "array":
            return isinstance(value, list)
        case "object":
            return isinstance(value, dict)
        case "null":
            return value is None
        case _:
            return False


def _weighted_score(sections: list[tuple[float, float]]) -> float:
    if not sections:
        return 1.0
    total_weight = sum(weight for weight, _ in sections)
    return sum(weight * score for weight, score in sections) / total_weight


def _get_threshold(config: dict[str, Any]) -> float:
    try:
        return float(config.get("threshold", 1.0))
    except (TypeError, ValueError):
        return 1.0


def _add_failure_mode(failure_modes: list[str], failure_mode: str) -> None:
    if failure_mode not in failure_modes:
        failure_modes.append(failure_mode)
