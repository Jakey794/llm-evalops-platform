import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cli import eval_gate
from app.models import Base, Dataset, EvalRun, ModelConfig, PromptVersion
from app.models import TestCase as CaseModel


@pytest.fixture
def gate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(eval_gate, "get_session_factory", lambda: session_factory)

    with session_factory() as db:
        dataset = Dataset(name="Gate Dataset", workflow_type="support_classification")
        prompt = PromptVersion(
            name="support_classification_baseline",
            workflow_type="support_classification",
            version_label="v1",
            template="Classify {{ ticket }}",
        )
        model = ModelConfig(
            provider="openai",
            model_name="gpt-4o-mini",
            temperature=0,
            max_output_tokens=64,
        )
        db.add_all([dataset, prompt, model])
        db.flush()
        db.add(
            CaseModel(
                dataset_id=dataset.id,
                external_id="gate-1",
                input_json={"ticket": "I was charged twice"},
                expected_output_json={
                    "category": "billing",
                    "priority": "high",
                    "routed_team": "billing_ops",
                },
                required_citations=[],
                tags=["billing"],
                difficulty="easy",
                workflow_type="support_classification",
                metadata_json={
                    "grader_config": {
                        "json_schema": {
                            "required_fields": ["category", "priority", "routed_team"],
                            "field_types": {
                                "category": "string",
                                "priority": "string",
                                "routed_team": "string",
                            },
                        },
                        "exact_match": {"exact_fields": ["category", "priority", "routed_team"]},
                        "composite": {
                            "graders": [
                                {"name": "json_schema", "weight": 0.2},
                                {"name": "exact_match", "weight": 0.8},
                            ],
                            "pass_threshold": 0.9,
                        },
                    }
                },
            )
        )
        db.commit()
        ids = {
            "dataset_id": str(dataset.id),
            "prompt_version_id": str(prompt.id),
            "model_config_id": str(model.id),
            "dataset_name": dataset.name,
            "prompt_name": prompt.name,
            "model_name": model.model_name,
        }

    yield session_factory, ids, tmp_path
    engine.dispose()


def test_evaluate_thresholds_detects_violations() -> None:
    run = EvalRun(
        id=uuid4(),
        dataset_id=uuid4(),
        prompt_version_id=uuid4(),
        model_config_id=uuid4(),
        status="completed",
        pass_rate=0.5,
        avg_score=0.7,
        total_cost_usd=Decimal("1.5"),
        p95_latency_ms=900,
    )
    violations = eval_gate.evaluate_thresholds(
        run,
        eval_gate.GateThresholds(
            min_pass_rate=0.9,
            min_avg_score=0.8,
            max_cost_usd=1.0,
            max_p95_latency_ms=500,
        ),
    )
    assert {item.metric for item in violations} == {
        "pass_rate",
        "avg_score",
        "total_cost_usd",
        "p95_latency_ms",
    }


def test_cli_mock_gate_passes_and_writes_report(gate_db) -> None:
    _session_factory, ids, tmp_path = gate_db
    report_path = tmp_path / "report.json"

    exit_code = eval_gate.main(
        [
            "--dataset-name",
            ids["dataset_name"],
            "--prompt-name",
            ids["prompt_name"],
            "--model-name",
            ids["model_name"],
            "--min-pass-rate",
            "0.9",
            "--min-avg-score",
            "0.9",
            "--max-cost-usd",
            "1.0",
            "--max-p95-latency-ms",
            "1000",
            "--mock",
            "--report-path",
            str(report_path),
        ]
    )

    assert exit_code == eval_gate.EXIT_PASS
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["metrics"]["pass_rate"] == 1.0
    assert payload["violations"] == []


def test_cli_threshold_failure_exit_code(gate_db) -> None:
    _session_factory, ids, tmp_path = gate_db
    report_path = tmp_path / "fail.json"

    exit_code = eval_gate.main(
        [
            "--dataset-id",
            ids["dataset_id"],
            "--prompt-version-id",
            ids["prompt_version_id"],
            "--model-config-id",
            ids["model_config_id"],
            "--max-p95-latency-ms",
            "1",
            "--mock",
            "--report-path",
            str(report_path),
        ]
    )

    assert exit_code == eval_gate.EXIT_THRESHOLD_FAILURE
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert payload["violations"][0]["metric"] == "p95_latency_ms"


def test_cli_config_error_without_thresholds(tmp_path: Path) -> None:
    report_path = tmp_path / "config.json"
    exit_code = eval_gate.main(["--dataset-name", "x", "--report-path", str(report_path)])
    assert exit_code == eval_gate.EXIT_CONFIG_ERROR


def test_cli_config_error_for_missing_dataset(gate_db) -> None:
    _session_factory, _ids, tmp_path = gate_db
    report_path = tmp_path / "missing.json"
    exit_code = eval_gate.main(
        [
            "--dataset-name",
            "does-not-exist",
            "--prompt-name",
            "support_classification_baseline",
            "--model-name",
            "gpt-4o-mini",
            "--min-pass-rate",
            "0.5",
            "--mock",
            "--report-path",
            str(report_path),
        ]
    )
    assert exit_code == eval_gate.EXIT_CONFIG_ERROR
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert "Dataset not found" in payload["error"]
