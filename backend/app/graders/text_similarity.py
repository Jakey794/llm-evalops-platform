import json
import string
from difflib import SequenceMatcher
from typing import Any

from app.graders.base import BaseGrader, GraderInput, GraderResult, clamp_score

_PUNCTUATION_TABLE = str.maketrans("", "", string.punctuation)
_MISSING = object()


class TextSimilarityGrader(BaseGrader):
    name = "text_similarity"

    def grade(self, input: GraderInput) -> GraderResult:
        config = _get_config(input.grader_config)
        phrases = _get_phrases(config.get("answer_contains"))
        if not phrases and isinstance(input.expected_output, dict):
            phrases = _get_phrases(input.expected_output.get("answer_contains"))

        expected_text = _get_expected_text(input, config, phrases)
        actual_text = _get_actual_text(input, config)

        if not expected_text and not phrases:
            return GraderResult(
                grader_name=self.name,
                score=0.0,
                passed=False,
                feedback="Expected text is missing.",
                failure_modes=["missing_expected_text"],
            )
        if not actual_text:
            return GraderResult(
                grader_name=self.name,
                score=0.0,
                passed=False,
                feedback="Actual text is missing.",
                failure_modes=["missing_actual_text"],
            )

        normalize_case = bool(config.get("normalize_case", True))
        strip_punctuation = bool(config.get("strip_punctuation", True))
        normalized_expected = _normalize(
            expected_text or " ".join(phrases), normalize_case, strip_punctuation
        )
        normalized_actual = _normalize(actual_text, normalize_case, strip_punctuation)

        similarity_score = SequenceMatcher(
            None,
            normalized_expected,
            normalized_actual,
        ).ratio()
        matched_phrases = [
            phrase
            for phrase in phrases
            if _normalize(phrase, normalize_case, strip_punctuation) in normalized_actual
        ]
        contains_score = len(matched_phrases) / len(phrases) if phrases else 0.0
        final_score = max(similarity_score, contains_score) if phrases else similarity_score
        final_score = clamp_score(final_score)
        threshold = _get_threshold(config)

        failure_modes: list[str] = []
        if len(matched_phrases) < len(phrases):
            failure_modes.append("missing_required_phrase")
        if final_score < threshold:
            failure_modes.append("low_text_similarity")

        feedback = f"Text similarity: {similarity_score:.3f}."
        if phrases:
            feedback += f" Matched {len(matched_phrases)}/{len(phrases)} required phrases."

        return GraderResult(
            grader_name=self.name,
            score=final_score,
            passed=final_score >= threshold,
            feedback=feedback,
            failure_modes=failure_modes,
            metadata={
                "similarity_score": similarity_score,
                "contains_score": contains_score,
            },
        )


def _get_config(grader_config: dict[str, Any]) -> dict[str, Any]:
    config = grader_config.get("text_similarity", grader_config)
    return config if isinstance(config, dict) else {}


def _get_phrases(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _get_expected_text(
    input: GraderInput,
    config: dict[str, Any],
    phrases: list[str],
) -> str | None:
    expected_field = config.get("expected_field")
    if isinstance(expected_field, str) and isinstance(input.expected_output, dict):
        value = _get_path(input.expected_output, expected_field)
        return None if value is _MISSING else _stringify(value)
    if isinstance(input.expected_output, str):
        return input.expected_output
    if phrases:
        return " ".join(phrases)
    return None


def _get_actual_text(input: GraderInput, config: dict[str, Any]) -> str | None:
    actual_field = config.get("actual_field")
    if isinstance(actual_field, str):
        source = _get_actual_object(input)
        if source is None:
            return None
        value = _get_path(source, actual_field)
        return None if value is _MISSING else _stringify(value)

    if isinstance(input.model_output, str):
        return input.model_output
    if input.parsed_output is not None:
        return _stringify(input.parsed_output)
    return _stringify(input.model_output)


def _get_actual_object(input: GraderInput) -> dict[str, Any] | None:
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


def _get_path(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def _normalize(value: str, normalize_case: bool, strip_punctuation: bool) -> str:
    if strip_punctuation:
        value = value.translate(_PUNCTUATION_TABLE)
    value = " ".join(value.split())
    return value.casefold() if normalize_case else value


def _get_threshold(config: dict[str, Any]) -> float:
    try:
        return float(config.get("threshold", 0.75))
    except (TypeError, ValueError):
        return 0.75
