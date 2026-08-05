from dataclasses import dataclass

ALLOWED_FAILURE_MODES = (
    "incorrect_label",
    "invalid_json",
    "missing_required_field",
    "wrong_severity",
    "incomplete_reasoning",
    "unsupported_claim",
    "missing_citation",
    "hallucination",
    "irrelevant_answer",
)


@dataclass(frozen=True)
class RubricCriterion:
    name: str
    description: str


@dataclass(frozen=True)
class JudgeRubric:
    workflow_type: str
    description: str
    criteria: tuple[RubricCriterion, ...]
    pass_threshold: float = 0.8


INCIDENT_TRIAGE_RUBRIC = JudgeRubric(
    workflow_type="incident_triage",
    description="Evaluate whether the response accurately and usefully triages the incident.",
    criteria=(
        RubricCriterion(
            "severity_accuracy",
            "The severity matches the observed impact and the expected severity.",
        ),
        RubricCriterion(
            "service_identification",
            "The impacted service is identified correctly.",
        ),
        RubricCriterion(
            "root_cause_quality",
            "The proposed root cause is supported by the symptoms and expected output.",
        ),
        RubricCriterion(
            "summary_quality",
            "The summary is concise, complete, and operationally useful.",
        ),
    ),
)

SUPPORT_CLASSIFICATION_RUBRIC = JudgeRubric(
    workflow_type="support_classification",
    description=(
        "Evaluate whether the response routes and prioritizes the support request correctly."
    ),
    criteria=(
        RubricCriterion(
            "category_accuracy",
            "The category matches the request and expected classification.",
        ),
        RubricCriterion(
            "priority_accuracy",
            "The priority reflects the urgency and matches the expected output when provided.",
        ),
        RubricCriterion(
            "routing_accuracy",
            "The selected team is appropriate and matches the expected route when provided.",
        ),
        RubricCriterion(
            "classification_relevance",
            "The classification is focused on the user's actual support need.",
        ),
    ),
)

RAG_QA_RUBRIC = JudgeRubric(
    workflow_type="rag_qa",
    description=(
        "Evaluate answer quality and grounding against the supplied documents and "
        "expected output. Deterministic citation grading remains authoritative for "
        "missing_citation and invalid_citation."
    ),
    criteria=(
        RubricCriterion(
            "answer_correctness",
            "The answer agrees with the expected output and supplied documents.",
        ),
        RubricCriterion(
            "answer_completeness",
            "The answer covers the important parts of the question.",
        ),
        RubricCriterion(
            "answer_relevance",
            "The answer is direct and relevant to the question.",
        ),
        RubricCriterion(
            "claim_support",
            "Claims are supported by the cited documents and expected output.",
        ),
    ),
)

GENERIC_RUBRIC = JudgeRubric(
    workflow_type="generic",
    description="Evaluate the response against the supplied input and expected output.",
    criteria=(
        RubricCriterion("correctness", "The response agrees with the expected output."),
        RubricCriterion("completeness", "The response includes the required information."),
        RubricCriterion("relevance", "The response directly addresses the input."),
    ),
)

WORKFLOW_RUBRICS = {
    rubric.workflow_type: rubric
    for rubric in (
        INCIDENT_TRIAGE_RUBRIC,
        SUPPORT_CLASSIFICATION_RUBRIC,
        RAG_QA_RUBRIC,
    )
}


def get_rubric(workflow_type: str) -> JudgeRubric:
    """Return the configured rubric or the generic fallback for an unknown workflow."""
    return WORKFLOW_RUBRICS.get(workflow_type.strip().lower(), GENERIC_RUBRIC)
