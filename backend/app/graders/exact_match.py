import json
from typing import Any

from app.graders.base import BaseGrader, GraderInput, GraderResult

_MISSING = object()


class ExactMatchGrader(BaseGrader):
    name = "exact_match"

    def grade(self, input: GraderInput) -> GraderResult:
        config = _get_config(input.grader_config)
        exact_fields = _get_exact_fields(config)

        if not exact_fields:
            return GraderResult(
                grader_name=self.name,
                score=1.0,
                passed=True,
                feedback="No exact fields configured; exact match passed by default.",
            )

        expected = _as_object(input.expected_output)
        actual = input.parsed_output or _as_object(input.model_output)
        case_sensitive = bool(config.get("case_sensitive", False))
        normalize_whitespace = bool(config.get("normalize_whitespace", True))
        threshold = _get_threshold(config)

        matched_fields = 0
        failure_modes: list[str] = []
        details: list[str] = []

        for field in exact_fields:
            expected_value = _get_path(expected, field)
            actual_value = _get_path(actual, field)

            if expected_value is _MISSING:
                _add_failure_mode(failure_modes, "missing_expected_field")
                details.append(f"{field} is missing from expected output.")
                continue
            if actual_value is _MISSING:
                _add_failure_mode(failure_modes, "missing_actual_field")
                details.append(f"{field} is missing from actual output.")
                continue
            if _normalize(expected_value, case_sensitive, normalize_whitespace) == _normalize(
                actual_value,
                case_sensitive,
                normalize_whitespace,
            ):
                matched_fields += 1
                continue

            _add_failure_mode(failure_modes, "field_mismatch")
            details.append(f"{field} expected {expected_value!r} but got {actual_value!r}.")

        score = matched_fields / len(exact_fields)
        feedback = f"Matched {matched_fields}/{len(exact_fields)} exact fields."
        if details:
            feedback = f"{feedback} {' '.join(details)}"

        return GraderResult(
            grader_name=self.name,
            score=score,
            passed=score >= threshold,
            feedback=feedback,
            failure_modes=failure_modes,
        )


def _get_config(grader_config: dict[str, Any]) -> dict[str, Any]:
    config = grader_config.get("exact_match", grader_config)
    return config if isinstance(config, dict) else {}


def _get_exact_fields(config: dict[str, Any]) -> list[str]:
    fields = config.get("exact_fields", [])
    if not isinstance(fields, list):
        return []
    return [field for field in fields if isinstance(field, str)]


def _get_threshold(config: dict[str, Any]) -> float:
    try:
        return float(config.get("threshold", 1.0))
    except (TypeError, ValueError):
        return 1.0


def _as_object(value: dict[str, Any] | str | None) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}

    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _get_path(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _normalize(value: Any, case_sensitive: bool, normalize_whitespace: bool) -> Any:
    if not isinstance(value, str):
        return value
    if normalize_whitespace:
        value = " ".join(value.split())
    if not case_sensitive:
        value = value.casefold()
    return value


def _add_failure_mode(failure_modes: list[str], failure_mode: str) -> None:
    if failure_mode not in failure_modes:
        failure_modes.append(failure_mode)
