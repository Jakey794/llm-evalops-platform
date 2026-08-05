import json

from app.graders import (
    ALLOWED_FAILURE_MODES,
    GENERIC_RUBRIC,
    build_llm_judge_prompt,
    get_rubric,
)


def test_judge_prompt_includes_evaluation_inputs_and_deterministic_summary() -> None:
    input_json = {"title": "Checkout unavailable", "symptoms": ["HTTP 503"]}
    expected_output_json = {"severity": "sev-1", "impacted_service": "checkout"}
    model_output = {"severity": "sev-2", "impacted_service": "checkout"}
    deterministic_summary = {"score": 0.5, "failure_modes": ["exact_mismatch"]}

    prompt = build_llm_judge_prompt(
        "incident_triage",
        input_json,
        expected_output_json,
        model_output,
        deterministic_summary,
    )

    assert json.dumps(input_json, indent=2, sort_keys=True) in prompt
    assert json.dumps(expected_output_json, indent=2, sort_keys=True) in prompt
    assert json.dumps(model_output, indent=2, sort_keys=True) in prompt
    assert json.dumps(deterministic_summary, indent=2, sort_keys=True) in prompt


def test_workflow_rubrics_are_distinct() -> None:
    incident = get_rubric("incident_triage")
    support = get_rubric("support_classification")

    assert incident != support
    assert {criterion.name for criterion in incident.criteria} != {
        criterion.name for criterion in support.criteria
    }


def test_unknown_workflow_uses_generic_fallback_rubric() -> None:
    rubric = get_rubric("new_workflow")
    prompt = build_llm_judge_prompt(
        "new_workflow",
        {"request": "Evaluate this"},
        {"result": "expected"},
        {"result": "actual"},
    )

    assert rubric is GENERIC_RUBRIC
    assert GENERIC_RUBRIC.description in prompt
    assert "Not available." in prompt


def test_prompt_requires_structured_output_and_allowed_failure_modes() -> None:
    prompt = build_llm_judge_prompt(
        "support_classification",
        {"ticket": "I cannot sign in"},
        {"category": "account_access"},
        '{"category":"account_access"}',
    )

    for field_name in ("score", "passed", "reason", "failure_modes", "rubric_scores"):
        assert field_name in prompt
    assert "Return only one JSON object" in prompt
    assert all(failure_mode in prompt for failure_mode in ALLOWED_FAILURE_MODES)


def test_rag_rubric_describes_grounding_and_defers_citations() -> None:
    rag_rubric = get_rubric("rag_qa")

    assert "grounding" in rag_rubric.description.lower()
    assert "missing_citation" in rag_rubric.description
    assert "invalid_citation" in rag_rubric.description
    assert {criterion.name for criterion in rag_rubric.criteria} >= {
        "answer_correctness",
        "claim_support",
    }
