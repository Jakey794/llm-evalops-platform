import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.dialects import postgresql, sqlite

from app.models import (
    Base,
    Dataset,
    EvalResult,
    EvalRun,
    ModelConfig,
    ModelProvider,
    PromptVersion,
)
from app.models import TestCase as CaseModel


def test_eval_runner_tables_are_registered_with_base_metadata() -> None:
    assert {
        "datasets",
        "test_cases",
        "prompt_versions",
        "model_configs",
        "eval_runs",
        "eval_results",
    } <= set(Base.metadata.tables)


def test_prompt_version_constraints_and_indexes() -> None:
    table = PromptVersion.__table__
    unique_constraint = next(
        constraint
        for constraint in table.constraints
        if constraint.name == "uq_prompt_versions_workflow_name_version"
    )

    assert tuple(unique_constraint.columns.keys()) == (
        "workflow_type",
        "name",
        "version_label",
    )
    assert any(index.columns.keys() == ["workflow_type"] for index in table.indexes)
    assert not table.c.template.nullable
    assert table.c.created_at.type.timezone


def test_model_config_uses_portable_jsonb_and_provider_index() -> None:
    table = ModelConfig.__table__

    assert table.c.response_format.type.compile(dialect=postgresql.dialect()) == "JSONB"
    assert table.c.response_format.type.compile(dialect=sqlite.dialect()) == "JSON"
    assert any(index.columns.keys() == ["provider"] for index in table.indexes)
    assert table.c.temperature.nullable
    assert not table.c.max_output_tokens.nullable


def test_eval_run_foreign_keys_defaults_and_indexes() -> None:
    table = EvalRun.__table__
    foreign_keys = {
        column_name: next(iter(table.c[column_name].foreign_keys))
        for column_name in ("dataset_id", "prompt_version_id", "model_config_id")
    }
    indexed_columns = {tuple(index.columns.keys()) for index in table.indexes}

    assert foreign_keys["dataset_id"].target_fullname == "datasets.id"
    assert foreign_keys["dataset_id"].ondelete == "CASCADE"
    assert foreign_keys["prompt_version_id"].ondelete == "RESTRICT"
    assert foreign_keys["model_config_id"].ondelete == "RESTRICT"
    assert {
        ("dataset_id",),
        ("prompt_version_id",),
        ("model_config_id",),
        ("status",),
    } <= indexed_columns
    assert table.c.started_at.nullable
    assert table.c.completed_at.nullable
    assert table.c.pass_rate.nullable
    assert table.c.avg_score.nullable
    assert table.c.avg_latency_ms.nullable
    assert table.c.p95_latency_ms.nullable
    assert table.c.total_cost_usd.type.precision == 14
    assert table.c.total_cost_usd.type.scale == 8
    assert not table.c.failed_count.nullable


def test_eval_result_constraints_json_types_and_foreign_keys() -> None:
    table = EvalResult.__table__
    unique_constraint = next(
        constraint
        for constraint in table.constraints
        if constraint.name == "uq_eval_results_run_test_case"
    )
    eval_run_fk = next(iter(table.c.eval_run_id.foreign_keys))
    test_case_fk = next(iter(table.c.test_case_id.foreign_keys))

    assert tuple(unique_constraint.columns.keys()) == ("eval_run_id", "test_case_id")
    assert eval_run_fk.target_fullname == "eval_runs.id"
    assert eval_run_fk.ondelete == "CASCADE"
    assert test_case_fk.target_fullname == "test_cases.id"
    assert test_case_fk.ondelete == "CASCADE"
    for column_name in ("parsed_output", "raw_response", "failure_modes", "grader_breakdown"):
        column_type = table.c[column_name].type
        assert column_type.compile(dialect=postgresql.dialect()) == "JSONB"
        assert column_type.compile(dialect=sqlite.dialect()) == "JSON"
    assert not table.c.score.nullable
    assert not table.c.passed.nullable
    assert not table.c.grader_feedback.nullable


def test_eval_runner_relationships_are_bidirectional_with_expected_cascades() -> None:
    dataset_runs = Dataset.__mapper__.relationships["eval_runs"]
    test_case_results = CaseModel.__mapper__.relationships["eval_results"]
    run_results = EvalRun.__mapper__.relationships["results"]
    prompt_runs = PromptVersion.__mapper__.relationships["eval_runs"]
    model_runs = ModelConfig.__mapper__.relationships["eval_runs"]

    assert dataset_runs.back_populates == "dataset"
    assert dataset_runs.cascade.delete_orphan
    assert dataset_runs.passive_deletes
    assert test_case_results.back_populates == "test_case"
    assert test_case_results.cascade.delete
    assert test_case_results.passive_deletes
    assert run_results.back_populates == "eval_run"
    assert run_results.cascade.delete_orphan
    assert run_results.passive_deletes
    assert prompt_runs.passive_deletes == "all"
    assert model_runs.passive_deletes == "all"


def test_eval_runner_object_graph_links_existing_dataset_and_test_case() -> None:
    now = datetime.now(UTC)
    dataset = Dataset(
        id=uuid.uuid4(),
        name="Support regression set",
        description=None,
        workflow_type="support",
        source_filename=None,
        created_at=now,
    )
    test_case = CaseModel(
        id=uuid.uuid4(),
        dataset=dataset,
        external_id="support-001",
        input_json={"message": "Help"},
        expected_output_json={"category": "support"},
        required_citations=[],
        tags=[],
        difficulty="easy",
        workflow_type="support",
        metadata_json={},
        created_at=now,
    )
    prompt = PromptVersion(
        id=uuid.uuid4(),
        name="support-router",
        workflow_type="support",
        template="Classify: {{ message }}",
        version_label="v1",
        created_at=now,
    )
    model_config = ModelConfig(
        id=uuid.uuid4(),
        provider=ModelProvider.OPENAI.value,
        model_name="gpt-4o-mini",
        temperature=None,
        max_output_tokens=256,
        response_format={"type": "json_object"},
        created_at=now,
    )
    eval_result = EvalResult(
        id=uuid.uuid4(),
        test_case=test_case,
        model_output='{"category":"support"}',
        parsed_output={"category": "support"},
        raw_response={"id": "response-1"},
        latency_ms=125.5,
        input_tokens=12,
        output_tokens=4,
        estimated_cost_usd=Decimal("0.00001234"),
        error=None,
        score=1.0,
        passed=True,
        grader_feedback="Matched expected output.",
        failure_modes=[],
        grader_breakdown={"breakdown": {"exact_match": 1.0}},
        created_at=now,
    )
    eval_run = EvalRun(
        id=uuid.uuid4(),
        dataset=dataset,
        prompt_version=prompt,
        model_config=model_config,
        status="completed",
        created_at=now,
        started_at=now,
        completed_at=now,
        total_cases=1,
        completed_cases=1,
        pass_rate=None,
        avg_score=None,
        total_cost_usd=Decimal("0.00001234"),
        avg_latency_ms=125.5,
        p95_latency_ms=125.5,
        error_count=0,
        failed_count=0,
        results=[eval_result],
    )

    assert eval_run in dataset.eval_runs
    assert eval_run in prompt.eval_runs
    assert eval_run in model_config.eval_runs
    assert eval_result.eval_run is eval_run
    assert eval_result in test_case.eval_results
