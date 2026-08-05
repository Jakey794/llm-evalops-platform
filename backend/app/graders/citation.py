import json
from typing import Any

from app.graders.base import BaseGrader, GraderInput, GraderResult, clamp_score


class CitationGrader(BaseGrader):
    """Deterministic citation and grounding checks for rag_qa workflows."""

    name = "citation"

    def grade(self, input: GraderInput) -> GraderResult:
        config = _get_config(input.grader_config)
        documents = _extract_documents(input.input_data)
        document_ids = {doc_id for doc_id, _ in documents}

        required = _unique_strings(config.get("required_citations"))
        if not required:
            required = _unique_strings(input.grader_config.get("required_citations"))
        if not required and isinstance(input.expected_output, dict):
            required = _unique_strings(input.expected_output.get("citations"))

        actual = _as_object(input.parsed_output or input.model_output)
        cited = _unique_strings(actual.get("citations"))
        answer = _as_text(actual.get("answer"))
        threshold = _get_threshold(config)

        failure_modes: list[str] = []
        details: list[str] = []

        missing = [citation for citation in required if citation not in cited]
        if missing:
            failure_modes.append("missing_citation")
            details.append(f"Missing required citations: {', '.join(missing)}.")

        invalid = [citation for citation in cited if citation not in document_ids]
        if invalid:
            failure_modes.append("invalid_citation")
            details.append(f"Invalid citations (not in documents): {', '.join(invalid)}.")

        grounded_claims = _unique_strings(config.get("required_claims"))
        if not grounded_claims and isinstance(input.expected_output, dict):
            grounded_claims = _unique_strings(input.expected_output.get("answer_contains"))
        unsupported = [
            claim for claim in grounded_claims if claim.casefold() not in answer.casefold()
        ]
        # Claims must also appear in at least one cited document when documents exist.
        if documents and cited:
            cited_text = " ".join(
                content for doc_id, content in documents if doc_id in set(cited)
            ).casefold()
            for claim in grounded_claims:
                if claim.casefold() in answer.casefold() and claim.casefold() not in cited_text:
                    if claim not in unsupported:
                        unsupported.append(claim)
        if unsupported:
            failure_modes.append("unsupported_claim")
            details.append(f"Unsupported claims: {', '.join(unsupported)}.")

        citation_score = 1.0
        if required:
            citation_score = (len(required) - len(missing)) / len(required)
        invalid_penalty = 0.0 if not cited else len(invalid) / len(cited)
        claim_score = (
            1.0
            if not grounded_claims
            else (len(grounded_claims) - len(unsupported)) / len(grounded_claims)
        )
        score = clamp_score(0.5 * citation_score + 0.5 * claim_score - 0.25 * invalid_penalty)

        feedback = (
            f"Citation score {score:.3f}. "
            f"Required {len(required)}, cited {len(cited)}, missing {len(missing)}, "
            f"invalid {len(invalid)}, unsupported claims {len(unsupported)}."
        )
        if details:
            feedback = f"{feedback} {' '.join(details)}"

        return GraderResult(
            grader_name=self.name,
            score=score,
            passed=score >= threshold and not failure_modes,
            feedback=feedback,
            failure_modes=failure_modes,
            metadata={
                "required_citations": required,
                "cited": cited,
                "missing": missing,
                "invalid": invalid,
                "unsupported_claims": unsupported,
                "document_ids": sorted(document_ids),
            },
        )


def _get_config(grader_config: dict[str, Any]) -> dict[str, Any]:
    config = grader_config.get("citation", grader_config)
    return config if isinstance(config, dict) else {}


def _get_threshold(config: dict[str, Any]) -> float:
    try:
        return float(config.get("threshold", 1.0))
    except (TypeError, ValueError):
        return 1.0


def _extract_documents(input_data: dict[str, Any] | str) -> list[tuple[str, str]]:
    if not isinstance(input_data, dict):
        return []
    documents = input_data.get("documents")
    if not isinstance(documents, list):
        return []
    extracted: list[tuple[str, str]] = []
    for document in documents:
        if not isinstance(document, dict):
            continue
        doc_id = document.get("id")
        content = document.get("content")
        if isinstance(doc_id, str) and doc_id.strip() and isinstance(content, str):
            extracted.append((doc_id.strip(), content))
    return extracted


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


def _as_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _unique_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip() and item.strip() not in result:
            result.append(item.strip())
    return result
