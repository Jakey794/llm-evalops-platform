import math
from typing import Any

from app.graders.base import BaseGrader, GraderInput, GraderResult, clamp_score
from app.graders.citation import CitationGrader
from app.graders.exact_match import ExactMatchGrader
from app.graders.json_schema import JsonSchemaGrader
from app.graders.text_similarity import TextSimilarityGrader

GRADER_REGISTRY: dict[str, type[BaseGrader]] = {
    "exact_match": ExactMatchGrader,
    "json_schema": JsonSchemaGrader,
    "text_similarity": TextSimilarityGrader,
    "citation": CitationGrader,
}


class CompositeGrader(BaseGrader):
    name = "composite"

    def grade(self, input: GraderInput) -> GraderResult:
        config = _get_config(input.grader_config)
        specs = _get_specs(config, input)
        pass_threshold = _get_number(config.get("pass_threshold"), default=0.8)

        if not specs:
            return GraderResult(
                grader_name=self.name,
                score=0.0,
                passed=False,
                feedback="No component graders were configured or inferred.",
                failure_modes=["no_graders_configured"],
                metadata={
                    "breakdown": {},
                    "grader_results": [],
                    "pass_threshold": pass_threshold,
                    "weights": {},
                },
            )

        normalized_specs = _normalize_weights(specs)
        component_results: list[GraderResult] = []
        breakdown: dict[str, float] = {}
        weights: dict[str, float] = {}
        failure_modes: list[str] = []

        for grader_name, weight in normalized_specs:
            grader_type = GRADER_REGISTRY.get(grader_name)
            result = (
                grader_type().grade(input)
                if grader_type is not None
                else _unknown_grader_result(grader_name)
            )
            component_results.append(result)
            breakdown[result.grader_name] = result.score
            weights[result.grader_name] = weight
            for failure_mode in result.failure_modes:
                if failure_mode not in failure_modes:
                    failure_modes.append(failure_mode)

        final_score = clamp_score(
            sum(
                result.score * weight
                for result, (_, weight) in zip(component_results, normalized_specs, strict=True)
            )
        )
        summaries = " ".join(
            f"{result.grader_name}={result.score:.3f} ({result.feedback})"
            for result in component_results
        )
        feedback = (
            f"Composite score {final_score:.3f} with pass threshold {pass_threshold:.3f}. "
            f"{summaries}"
        )

        return GraderResult(
            grader_name=self.name,
            score=final_score,
            passed=final_score >= pass_threshold,
            feedback=feedback,
            failure_modes=failure_modes,
            metadata={
                "breakdown": breakdown,
                "grader_results": [result.model_dump(mode="json") for result in component_results],
                "pass_threshold": pass_threshold,
                "weights": weights,
            },
        )


def _get_config(grader_config: dict[str, Any]) -> dict[str, Any]:
    config = grader_config.get("composite", grader_config)
    return config if isinstance(config, dict) else {}


def _get_specs(config: dict[str, Any], input: GraderInput) -> list[tuple[str, float]]:
    configured_graders = config.get("graders")
    if isinstance(configured_graders, list) and configured_graders:
        return [_parse_spec(spec) for spec in configured_graders]
    return [(grader_name, 1.0) for grader_name in _infer_default_graders(input)]


def _parse_spec(spec: Any) -> tuple[str, float]:
    if not isinstance(spec, dict):
        return "unknown", 1.0
    raw_name = spec.get("name")
    grader_name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else "unknown"
    weight = _get_number(spec.get("weight"), default=1.0)
    return grader_name, max(0.0, weight)


def _infer_default_graders(input: GraderInput) -> list[str]:
    grader_config = input.grader_config
    inferred: list[str] = []

    if isinstance(grader_config.get("json_schema"), dict):
        inferred.append("json_schema")

    exact_config = grader_config.get("exact_match", grader_config)
    if isinstance(exact_config, dict) and _has_values(exact_config.get("exact_fields")):
        inferred.append("exact_match")

    text_config = grader_config.get("text_similarity", grader_config)
    has_answer_contains = isinstance(text_config, dict) and _has_values(
        text_config.get("answer_contains")
    )
    has_expected_field = isinstance(text_config, dict) and isinstance(
        text_config.get("expected_field"), str
    )
    expected_output = input.expected_output
    has_expected_text = isinstance(expected_output, str) and bool(expected_output.strip())
    has_expected_phrases = isinstance(expected_output, dict) and _has_values(
        expected_output.get("answer_contains")
    )
    if has_answer_contains or has_expected_field or has_expected_text or has_expected_phrases:
        inferred.append("text_similarity")

    citation_config = grader_config.get("citation")
    has_explicit_citation = isinstance(citation_config, dict)
    if input.workflow_type == "rag_qa" or has_explicit_citation:
        inferred.append("citation")

    return inferred


def _has_values(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _normalize_weights(specs: list[tuple[str, float]]) -> list[tuple[str, float]]:
    total_weight = sum(weight for _, weight in specs)
    if total_weight <= 0:
        equal_weight = 1.0 / len(specs)
        return [(grader_name, equal_weight) for grader_name, _ in specs]
    return [(grader_name, weight / total_weight) for grader_name, weight in specs]


def _get_number(value: Any, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _unknown_grader_result(grader_name: str) -> GraderResult:
    if grader_name == "unknown":
        feedback = "Grader configuration is missing a valid name."
    else:
        feedback = f"Unknown grader '{grader_name}'."
    return GraderResult(
        grader_name=grader_name,
        score=0.0,
        passed=False,
        feedback=feedback,
        failure_modes=["unknown_grader"],
    )
