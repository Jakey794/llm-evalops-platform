import json
from typing import Any

from app.graders import CitationGrader, GraderInput, GraderResult


def grade(
    *,
    input_data: dict[str, Any],
    expected_output: dict[str, Any],
    model_output: dict[str, Any] | str,
    grader_config: dict[str, Any] | None = None,
) -> GraderResult:
    return CitationGrader().grade(
        GraderInput(
            test_case_id="rag-1",
            workflow_type="rag_qa",
            input_data=input_data,
            expected_output=expected_output,
            model_output=model_output
            if isinstance(model_output, str)
            else json.dumps(model_output),
            parsed_output=model_output if isinstance(model_output, dict) else None,
            grader_config=grader_config or {},
        )
    )


DOCS = [
    {
        "id": "refund-policy",
        "title": "Refund Policy",
        "content": "Customers may request a full refund within 30 days of purchase.",
    },
    {
        "id": "sla-guide",
        "title": "SLA Guide",
        "content": "Severity-1 incidents require acknowledgment within 15 minutes.",
    },
]


def test_citation_grader_passes_with_required_citations_and_claims() -> None:
    result = grade(
        input_data={"question": "What is the refund window?", "documents": DOCS},
        expected_output={
            "answer": "Customers may request a full refund within 30 days of purchase.",
            "citations": ["refund-policy"],
            "answer_contains": ["30 days"],
        },
        model_output={
            "answer": "Customers may request a full refund within 30 days of purchase.",
            "citations": ["refund-policy"],
        },
        grader_config={"citation": {"required_citations": ["refund-policy"], "threshold": 1.0}},
    )
    assert result.passed is True
    assert result.score == 1.0
    assert result.failure_modes == []


def test_missing_citation_failure_mode() -> None:
    result = grade(
        input_data={"question": "Refund window?", "documents": DOCS},
        expected_output={"answer": "30 days", "citations": ["refund-policy"]},
        model_output={"answer": "Refunds are allowed within 30 days.", "citations": []},
        grader_config={
            "citation": {
                "required_citations": ["refund-policy"],
                "required_claims": ["30 days"],
            }
        },
    )
    assert result.passed is False
    assert "missing_citation" in result.failure_modes


def test_invalid_citation_failure_mode() -> None:
    result = grade(
        input_data={"question": "Refund window?", "documents": DOCS},
        expected_output={"answer": "30 days", "citations": ["refund-policy"]},
        model_output={
            "answer": "Refunds are allowed within 30 days.",
            "citations": ["refund-policy", "made-up-doc"],
        },
        grader_config={"citation": {"required_citations": ["refund-policy"]}},
    )
    assert "invalid_citation" in result.failure_modes


def test_unsupported_claim_failure_mode() -> None:
    result = grade(
        input_data={"question": "Refund window?", "documents": DOCS},
        expected_output={
            "answer": "30 days",
            "citations": ["refund-policy"],
            "answer_contains": ["30 days"],
        },
        model_output={
            "answer": "Refunds are allowed forever with free shipping.",
            "citations": ["refund-policy"],
        },
        grader_config={
            "citation": {
                "required_citations": ["refund-policy"],
                "required_claims": ["30 days"],
            }
        },
    )
    assert "unsupported_claim" in result.failure_modes
