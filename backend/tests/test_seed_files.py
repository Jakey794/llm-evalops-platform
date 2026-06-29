from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.seed.load_seed_data as seed_loader
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
    ("filename", "workflow_type"),
    [
        ("support_classification.jsonl", "support_classification"),
        ("incident_triage.jsonl", "incident_triage"),
    ],
)
def test_seed_file_has_exactly_25_valid_unique_cases(filename: str, workflow_type: str) -> None:
    cases = load_cases(filename)
    external_ids = [case.external_id for case in cases]

    assert len(cases) == 25
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


def test_seed_loader_imports_both_datasets_once(monkeypatch: pytest.MonkeyPatch) -> None:
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
    ]
    assert [(summary.status, summary.imported_count) for summary in second_run] == [
        ("skipped", 0),
        ("skipped", 0),
    ]

    with session_factory() as db:
        assert db.scalar(select(func.count(Dataset.id))) == 2
        assert db.scalar(select(func.count(CaseModel.id))) == 50

    engine.dispose()
