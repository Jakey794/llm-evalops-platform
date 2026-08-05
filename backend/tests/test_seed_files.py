from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.seed.load_seed_data as seed_loader
from app.graders import CompositeGrader, GraderInput
from app.models import Base, Dataset
from app.models import TestCase as CaseModel
from app.services.jsonl_importer import Difficulty, JsonlTestCase, parse_jsonl_test_cases

SEED_DIRECTORY = Path(__file__).parents[1] / "app" / "seed"
SUPPORT_CATEGORIES = {
    "billing",
    "bug_report",
    "account_access",
    "feature_request",
    "refund",
    "technical_support",
}
INCIDENT_SEVERITIES = {"sev-1", "sev-2", "sev-3", "sev-4"}


def load_cases(filename: str) -> list[JsonlTestCase]:
    result = parse_jsonl_test_cases((SEED_DIRECTORY / filename).read_text(encoding="utf-8"))
    assert result.errors == []
    assert result.rejected_count == 0
    return result.valid_cases


@pytest.mark.parametrize(
    ("filename", "workflow_type", "expected_count"),
    [
        ("support_classification.jsonl", "support_classification", 25),
        ("incident_triage.jsonl", "incident_triage", 25),
        ("rag_qa.jsonl", "rag_qa", 20),
    ],
)
def test_seed_file_has_valid_unique_cases(
    filename: str,
    workflow_type: str,
    expected_count: int,
) -> None:
    cases = load_cases(filename)
    external_ids = [case.external_id for case in cases]

    assert len(cases) == expected_count
    assert len(external_ids) == len(set(external_ids))
    assert {case.difficulty for case in cases} == {
        Difficulty.EASY,
        Difficulty.MEDIUM,
        Difficulty.HARD,
    }
    assert all(case.tags for case in cases)
    assert all(case.workflow_type == workflow_type for case in cases)


def test_support_categories_are_allowed() -> None:
    cases = load_cases("support_classification.jsonl")
    categories = {case.expected_output.get("category") for case in cases}

    assert categories <= SUPPORT_CATEGORIES
    assert categories == SUPPORT_CATEGORIES


def test_incident_outputs_have_allowed_severities_and_required_fields() -> None:
    cases = load_cases("incident_triage.jsonl")
    severities = {case.expected_output.get("severity") for case in cases}

    assert severities <= INCIDENT_SEVERITIES
    assert severities == INCIDENT_SEVERITIES
    assert all(case.expected_output.get("impacted_service") for case in cases)
    assert all(case.expected_output.get("likely_root_cause") for case in cases)


def test_incident_cases_exercise_all_deterministic_graders() -> None:
    cases = load_cases("incident_triage.jsonl")
    configured_cases = [case for case in cases if case.metadata.get("grader_config")]

    assert len(configured_cases) >= 10
    for case in configured_cases:
        assert case.expected_output.get("summary")
        grader_config = case.metadata["grader_config"]
        assert set(grader_config) == {
            "json_schema",
            "exact_match",
            "text_similarity",
            "composite",
        }
        assert [grader["name"] for grader in grader_config["composite"]["graders"]] == [
            "json_schema",
            "exact_match",
            "text_similarity",
        ]
        assert sum(
            grader["weight"] for grader in grader_config["composite"]["graders"]
        ) == pytest.approx(1.0)
        assert_seed_case_passes(case)


def test_support_cases_include_routing_fields_and_emphasize_exact_match() -> None:
    cases = load_cases("support_classification.jsonl")
    configured_cases = [case for case in cases if case.metadata.get("grader_config")]

    assert len(configured_cases) >= 10
    for case in configured_cases:
        assert case.expected_output.get("category")
        assert case.expected_output.get("priority")
        assert case.expected_output.get("routed_team")
        grader_config = case.metadata["grader_config"]
        graders = grader_config["composite"]["graders"]
        weights = {grader["name"]: grader["weight"] for grader in graders}
        assert weights["exact_match"] > weights["json_schema"]
        assert set(grader_config["exact_match"]["exact_fields"]) == {
            "category",
            "priority",
            "routed_team",
        }
        assert_seed_case_passes(case)


def test_rag_cases_require_documents_citations_and_citation_grader() -> None:
    cases = load_cases("rag_qa.jsonl")
    assert all(case.required_citations for case in cases)
    assert all(isinstance(case.input.get("documents"), list) for case in cases)
    assert all(case.input["documents"] for case in cases)
    for case in cases:
        grader_config = case.metadata["grader_config"]
        assert "citation" in grader_config
        assert [grader["name"] for grader in grader_config["composite"]["graders"]] == [
            "json_schema",
            "text_similarity",
            "citation",
        ]
        assert_seed_case_passes(case)


def test_seed_files_include_intentionally_tricky_cases() -> None:
    cases = (
        load_cases("incident_triage.jsonl")
        + load_cases("support_classification.jsonl")
        + load_cases("rag_qa.jsonl")
    )
    tricky_cases = [case for case in cases if case.metadata.get("tricky") is True]

    assert len(tricky_cases) >= 3
    assert all(case.metadata.get("tricky_reason") for case in tricky_cases)
    assert all("tricky" in case.tags for case in tricky_cases)


def assert_seed_case_passes(case: JsonlTestCase) -> None:
    result = CompositeGrader().grade(
        GraderInput(
            test_case_id=case.external_id,
            workflow_type=case.workflow_type,
            input_data=case.input,
            expected_output=case.expected_output,
            model_output=case.expected_output,
            parsed_output=case.expected_output,
            grader_config=case.metadata["grader_config"],
            tags=case.tags,
            difficulty=case.difficulty.value,
        )
    )

    assert result.score == pytest.approx(1.0)
    assert result.passed is True


def test_seed_loader_imports_all_datasets_once(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(seed_loader, "get_session_factory", lambda: session_factory)

    first_run = seed_loader.load_seed_data()
    second_run = seed_loader.load_seed_data()

    assert [(summary.status, summary.imported_count) for summary in first_run] == [
        ("imported", 25),
        ("imported", 25),
        ("imported", 20),
    ]
    assert [(summary.status, summary.imported_count) for summary in second_run] == [
        ("skipped", 0),
        ("skipped", 0),
        ("skipped", 0),
    ]

    with session_factory() as db:
        assert db.scalar(select(func.count(Dataset.id))) == 3
        assert db.scalar(select(func.count(CaseModel.id))) == 70

    engine.dispose()
