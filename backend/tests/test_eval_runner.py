import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import (
    Base,
    Dataset,
    EvalResult,
    EvalRun,
    EvalRunStatus,
    GraderResult,
    ModelConfig,
    PromptVersion,
)
from app.models import TestCase as CaseModel
from app.schemas import LLMJudgeOutput
from app.services.eval_runner import (
    EvalResourceNotFoundError,
    EvalRunner,
    EvalRunSetupError,
    default_provider_factory,
)
from app.services.judge_provider import JudgeProviderResult, JudgeUsage
from app.services.providers import LLMRequest, LLMResponse


class FakeProvider:
    def __init__(self, responses: list[LLMResponse | Exception]) -> None:
        self._responses = iter(responses)
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        response = next(self._responses)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with session_factory() as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


def make_response(
    text: str | None,
    *,
    parsed_json: dict[str, Any] | list[Any] | None = None,
    error: str | None = None,
    latency_ms: int = 25,
) -> LLMResponse:
    return LLMResponse(
        text=text,
        parsed_json=parsed_json,
        latency_ms=latency_ms,
        input_tokens=10,
        output_tokens=4,
        model_name="gpt-4o-mini-2024-07-18",
        raw_response={"id": f"response-{latency_ms}"},
        error=error,
    )


def seed_configuration(
    db: Session,
    *,
    workflow_type: str = "support_classification",
    prompt_workflow_type: str | None = None,
    case_inputs: list[dict[str, Any]] | None = None,
    grader_config: dict[str, Any] | None = None,
) -> tuple[Dataset, PromptVersion, ModelConfig, list[CaseModel]]:
    now = datetime.now(UTC)
    inputs = (
        case_inputs
        if case_inputs is not None
        else [
            {"ticket": "First ticket"},
            {"ticket": "Second ticket"},
        ]
    )
    dataset = Dataset(
        name="Support regression set",
        description=None,
        workflow_type=workflow_type,
        source_filename=None,
        test_cases=[
            CaseModel(
                external_id=f"case-{index}",
                input_json=input_json,
                expected_output_json={"category": "billing"},
                required_citations=[],
                tags=[],
                difficulty="easy",
                workflow_type=workflow_type,
                metadata_json=(
                    {"grader_config": grader_config} if grader_config is not None else {}
                ),
                created_at=now + timedelta(seconds=index),
            )
            for index, input_json in enumerate(inputs, start=1)
        ],
    )
    prompt_version = PromptVersion(
        name="support_baseline",
        workflow_type=prompt_workflow_type or workflow_type,
        template="Ticket: {{ ticket }}",
        version_label="v1",
    )
    model_config = ModelConfig(
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.2,
        max_output_tokens=128,
        response_format={"type": "json_object"},
    )
    db.add_all([dataset, prompt_version, model_config])
    db.commit()
    return dataset, prompt_version, model_config, list(dataset.test_cases)


def stored_results(db: Session, run_id: uuid.UUID) -> list[EvalResult]:
    return list(
        db.scalars(
            select(EvalResult)
            .join(CaseModel)
            .where(EvalResult.eval_run_id == run_id)
            .order_by(CaseModel.created_at, CaseModel.id)
        )
    )


def make_judge_result(
    *,
    score: float | None = None,
    passed: bool | None = None,
    error: str | None = None,
) -> JudgeProviderResult:
    output = (
        LLMJudgeOutput(
            score=score,
            passed=bool(passed),
            reason="Judge assessment.",
            failure_modes=[] if passed else ["incorrect_label"],
            rubric_scores={"correctness": score},
        )
        if score is not None
        else None
    )
    return JudgeProviderResult(
        judge_output=output,
        usage=JudgeUsage(input_tokens=20, output_tokens=8, total_tokens=28),
        latency_ms=40,
        model_name="gemini-2.5-flash-lite",
        raw_output={"response_id": "judge-1"},
        error=error,
    )


def all_grader_config() -> dict[str, Any]:
    return {
        "json_schema": {
            "required_fields": ["category"],
            "field_types": {"category": "string"},
        },
        "exact_match": {"exact_fields": ["category"]},
        "text_similarity": {
            "expected_field": "category",
            "actual_field": "category",
        },
        "composite": {
            "graders": [
                {"name": "json_schema", "weight": 1},
                {"name": "exact_match", "weight": 1},
                {"name": "text_similarity", "weight": 1},
            ],
            "pass_threshold": 0.8,
        },
        "llm_judge": {"enabled": True},
    }


def test_successful_run_creates_ordered_result_rows_and_requests(db: Session) -> None:
    dataset, prompt, model_config, test_cases = seed_configuration(db)
    provider = FakeProvider(
        [
            make_response('{"category":"billing"}', parsed_json={"category": "billing"}),
            make_response(
                '[{"category":"technical_support"}]',
                parsed_json=[{"category": "technical_support"}],
                latency_ms=35,
            ),
        ]
    )

    eval_run = EvalRunner(db, provider_factory=lambda _: provider).run(
        dataset.id,
        prompt.id,
        model_config.id,
    )
    results = stored_results(db, eval_run.id)

    assert eval_run.status == EvalRunStatus.COMPLETED.value
    assert eval_run.total_cases == 2
    assert eval_run.completed_cases == 2
    assert eval_run.error_count == 0
    assert eval_run.completed_at is not None
    assert eval_run.pass_rate == 0.5
    assert eval_run.avg_score == 0.5
    assert eval_run.failed_count == 1
    assert eval_run.total_count == 2
    assert eval_run.total_cost_usd == Decimal("0.00000780")
    assert eval_run.avg_latency_ms == 30
    assert eval_run.p95_latency_ms == 35
    assert [result.test_case_id for result in results] == [case.id for case in test_cases]
    assert results[0].parsed_output == {"category": "billing"}
    assert results[1].parsed_output == [{"category": "technical_support"}]
    assert results[0].score == 1.0
    assert results[0].passed is True
    assert results[0].grader_breakdown["breakdown"] == {
        "json_schema": 1.0,
        "exact_match": 1.0,
    }
    assert results[1].score == 0.0
    assert results[1].passed is False
    assert "invalid_json" in results[1].failure_modes
    assert [result.estimated_cost_usd for result in results] == [
        Decimal("0.00000390"),
        Decimal("0.00000390"),
    ]
    assert [request.prompt for request in provider.requests] == [
        "Ticket: First ticket",
        "Ticket: Second ticket",
    ]
    assert provider.requests[0].model_name == "gpt-4o-mini"
    assert provider.requests[0].temperature == 0.2
    assert provider.requests[0].max_output_tokens == 128
    assert provider.requests[0].response_format == {"type": "json_object"}
    assert provider.requests[0].metadata == {
        "eval_run_id": str(eval_run.id),
        "test_case_id": str(test_cases[0].id),
        "test_case_external_id": "case-1",
    }


def test_returned_provider_error_is_stored_and_run_completes(db: Session) -> None:
    dataset, prompt, model_config, _ = seed_configuration(db)
    provider = FakeProvider(
        [
            make_response(None, error="rate limited"),
            make_response('{"category":"billing"}', parsed_json={"category": "billing"}),
        ]
    )

    eval_run = EvalRunner(db, provider_factory=lambda _: provider).run(
        dataset.id,
        prompt.id,
        model_config.id,
    )
    results = stored_results(db, eval_run.id)

    assert eval_run.status == EvalRunStatus.COMPLETED.value
    assert eval_run.completed_cases == 2
    assert eval_run.error_count == 1
    assert eval_run.total_cost_usd == Decimal("0.00000780")
    assert eval_run.avg_latency_ms == 25
    assert eval_run.p95_latency_ms == 25
    assert results[0].error == "rate limited"
    assert results[1].error is None
    assert [result.passed for result in results] == [False, True]
    assert eval_run.pass_rate == 0.5
    assert eval_run.avg_score == 0.5
    assert eval_run.failed_count == 1


def test_raised_provider_error_is_stored_and_run_continues(db: Session) -> None:
    dataset, prompt, model_config, _ = seed_configuration(db)
    provider = FakeProvider(
        [
            RuntimeError("connection reset"),
            make_response('{"category":"billing"}', parsed_json={"category": "billing"}),
        ]
    )

    eval_run = EvalRunner(db, provider_factory=lambda _: provider).run(
        dataset.id,
        prompt.id,
        model_config.id,
    )
    results = stored_results(db, eval_run.id)

    assert eval_run.status == EvalRunStatus.COMPLETED.value
    assert eval_run.completed_cases == 2
    assert eval_run.error_count == 1
    assert eval_run.total_cost_usd == Decimal("0.00000390")
    assert eval_run.avg_latency_ms == 12.5
    assert eval_run.p95_latency_ms == 25
    assert results[0].error == "RuntimeError: connection reset"
    assert results[1].error is None
    assert results[0].passed is False
    assert "provider_error" in results[0].failure_modes


def test_render_error_is_isolated_to_its_case(db: Session) -> None:
    dataset, prompt, model_config, _ = seed_configuration(
        db,
        case_inputs=[{"ticket": "Valid ticket"}, {"unrelated": "missing ticket"}],
    )
    provider = FakeProvider(
        [make_response('{"category":"billing"}', parsed_json={"category": "billing"})]
    )

    eval_run = EvalRunner(db, provider_factory=lambda _: provider).run(
        dataset.id,
        prompt.id,
        model_config.id,
    )
    results = stored_results(db, eval_run.id)

    assert eval_run.completed_cases == 2
    assert eval_run.error_count == 1
    assert results[0].error is None
    assert (
        results[1].error == "MissingPromptVariableError: Missing required prompt variable: ticket"
    )
    assert len(provider.requests) == 1
    assert results[1].passed is False
    assert "provider_error" in results[1].failure_modes


def test_invalid_json_is_stored_and_graded_as_failed(db: Session) -> None:
    dataset, prompt, model_config, _ = seed_configuration(
        db,
        case_inputs=[{"ticket": "Malformed response"}],
        grader_config={
            "json_schema": {
                "required_fields": ["category"],
                "field_types": {"category": "string"},
            }
        },
    )
    provider = FakeProvider([make_response("{not-json", parsed_json=None)])

    eval_run = EvalRunner(db, provider_factory=lambda _: provider).run(
        dataset.id,
        prompt.id,
        model_config.id,
    )
    result = stored_results(db, eval_run.id)[0]

    assert result.model_output == "{not-json"
    assert result.parsed_output is None
    assert result.error is None
    assert result.score == 0.0
    assert result.passed is False
    assert result.failure_modes == ["invalid_json"]
    assert eval_run.pass_rate == 0.0
    assert eval_run.avg_score == 0.0
    assert eval_run.failed_count == 1


def test_runner_parses_valid_json_when_provider_omits_parsed_output(db: Session) -> None:
    dataset, prompt, model_config, _ = seed_configuration(
        db,
        case_inputs=[{"ticket": "Valid JSON response"}],
    )
    provider = FakeProvider([make_response('{"category":"billing"}', parsed_json=None)])

    eval_run = EvalRunner(db, provider_factory=lambda _: provider).run(
        dataset.id,
        prompt.id,
        model_config.id,
    )
    result = stored_results(db, eval_run.id)[0]

    assert result.parsed_output == {"category": "billing"}
    assert result.score == 1.0
    assert result.passed is True


def test_explicit_test_case_grader_config_takes_precedence(db: Session) -> None:
    dataset, prompt, model_config, _ = seed_configuration(
        db,
        case_inputs=[{"ticket": "Explicit grader config"}],
        grader_config={
            "composite": {
                "graders": [{"name": "exact_match", "weight": 1}],
                "pass_threshold": 0.0,
            },
            "exact_match": {"exact_fields": ["category"]},
        },
    )
    provider = FakeProvider(
        [
            make_response(
                '{"category":"technical_support"}',
                parsed_json={"category": "technical_support"},
            )
        ]
    )

    eval_run = EvalRunner(db, provider_factory=lambda _: provider).run(
        dataset.id,
        prompt.id,
        model_config.id,
    )
    result = stored_results(db, eval_run.id)[0]

    assert result.score == 0.0
    assert result.passed is True
    assert result.grader_breakdown["breakdown"] == {"exact_match": 0.0}


def test_deterministic_pass_and_judge_fail_uses_support_weights_and_persists_graders(
    db: Session,
) -> None:
    dataset, prompt, model_config, _ = seed_configuration(
        db,
        case_inputs=[{"ticket": "Billing question"}],
        grader_config=all_grader_config(),
    )
    provider = FakeProvider(
        [make_response('{"category":"billing"}', parsed_json={"category": "billing"})]
    )
    judge_function = Mock(return_value=make_judge_result(score=0.0, passed=False))

    eval_run = EvalRunner(
        db,
        provider_factory=lambda _: provider,
        judge_function=judge_function,
    ).run(dataset.id, prompt.id, model_config.id)
    result = stored_results(db, eval_run.id)[0]
    grader_rows = list(
        db.scalars(select(GraderResult).where(GraderResult.eval_result_id == result.id))
    )

    assert result.score == pytest.approx(0.7)
    assert result.passed is False
    assert result.grader_breakdown["composite"] == {
        "deterministic_score": 1.0,
        "deterministic_weight": 0.7,
        "llm_judge_score": 0.0,
        "llm_judge_weight": 0.3,
        "pass_threshold": 0.8,
        "score": 0.7,
    }
    assert {row.grader_name for row in grader_rows} == {
        "exact_match",
        "json_schema",
        "llm_judge",
        "text_similarity",
    }
    assert all(row.eval_result_id == result.id for row in grader_rows)
    assert {row.grader_type for row in grader_rows if row.grader_name != "llm_judge"} == {
        "deterministic"
    }
    judge_row = next(row for row in grader_rows if row.grader_name == "llm_judge")
    assert judge_row.grader_type == "llm"
    assert judge_row.score == 0.0
    assert judge_row.raw_output["latency_ms"] == 40
    assert judge_row.raw_output["usage"] == {
        "input_tokens": 20,
        "output_tokens": 8,
        "total_tokens": 28,
    }
    judge_function.assert_called_once()


def test_deterministic_fail_and_judge_pass_does_not_blindly_pass_incident(db: Session) -> None:
    grader_config = {
        "exact_match": {"exact_fields": ["category"]},
        "composite": {
            "graders": [{"name": "exact_match", "weight": 1}],
            "pass_threshold": 1.0,
        },
        "llm_judge": {"enabled": True},
    }
    dataset, prompt, model_config, _ = seed_configuration(
        db,
        workflow_type="incident_triage",
        case_inputs=[{"ticket": "Incident"}],
        grader_config=grader_config,
    )
    provider = FakeProvider(
        [
            make_response(
                '{"category":"technical_support"}',
                parsed_json={"category": "technical_support"},
            )
        ]
    )
    judge_function = Mock(return_value=make_judge_result(score=1.0, passed=True))

    eval_run = EvalRunner(
        db,
        provider_factory=lambda _: provider,
        judge_function=judge_function,
    ).run(dataset.id, prompt.id, model_config.id)
    result = stored_results(db, eval_run.id)[0]

    assert result.score == pytest.approx(0.6)
    assert result.passed is False
    assert result.grader_breakdown["composite"]["deterministic_weight"] == 0.4
    assert result.grader_breakdown["composite"]["llm_judge_weight"] == 0.6


def test_judge_provider_error_is_persisted_and_deterministic_result_survives(
    db: Session,
) -> None:
    dataset, prompt, model_config, _ = seed_configuration(
        db,
        case_inputs=[{"ticket": "Billing question"}],
        grader_config={
            "exact_match": {"exact_fields": ["category"]},
            "composite": {
                "graders": [{"name": "exact_match", "weight": 1}],
                "pass_threshold": 1.0,
            },
            "llm_judge": {"enabled": True},
        },
    )
    provider = FakeProvider(
        [make_response('{"category":"billing"}', parsed_json={"category": "billing"})]
    )
    judge_function = Mock(
        return_value=make_judge_result(error="Gemini judge provider error: unavailable")
    )

    eval_run = EvalRunner(
        db,
        provider_factory=lambda _: provider,
        judge_function=judge_function,
    ).run(dataset.id, prompt.id, model_config.id)
    result = stored_results(db, eval_run.id)[0]
    judge_row = db.scalar(
        select(GraderResult).where(
            GraderResult.eval_result_id == result.id,
            GraderResult.grader_name == "llm_judge",
        )
    )

    assert eval_run.status == EvalRunStatus.COMPLETED.value
    assert eval_run.error_count == 0
    assert result.score == 1.0
    assert result.passed is True
    assert judge_row is not None
    assert judge_row.score is None
    assert judge_row.passed is None
    assert judge_row.error == "Gemini judge provider error: unavailable"
    assert result.grader_breakdown["llm_judge"]["error"] == judge_row.error


@pytest.mark.parametrize(
    ("missing_resource", "expected_type"),
    [
        ("dataset", "Dataset"),
        ("prompt", "PromptVersion"),
        ("model", "ModelConfig"),
    ],
)
def test_missing_resource_raises_without_creating_run(
    db: Session,
    missing_resource: str,
    expected_type: str,
) -> None:
    dataset, prompt, model_config, _ = seed_configuration(db)
    ids = {
        "dataset": dataset.id,
        "prompt": prompt.id,
        "model": model_config.id,
    }
    ids[missing_resource] = uuid.uuid4()

    with pytest.raises(EvalResourceNotFoundError) as exc_info:
        EvalRunner(db, provider_factory=lambda _: FakeProvider([])).run(
            ids["dataset"],
            ids["prompt"],
            ids["model"],
        )

    assert exc_info.value.resource_type == expected_type
    assert exc_info.value.resource_id == ids[missing_resource]
    assert db.scalar(select(func.count(EvalRun.id))) == 0


def test_workflow_mismatch_persists_failed_run_and_raises(db: Session) -> None:
    dataset, prompt, model_config, _ = seed_configuration(
        db,
        prompt_workflow_type="incident_triage",
    )
    factory = Mock()

    with pytest.raises(EvalRunSetupError) as exc_info:
        EvalRunner(db, provider_factory=factory).run(dataset.id, prompt.id, model_config.id)

    assert exc_info.value.run_id is not None
    failed_run = db.get(EvalRun, exc_info.value.run_id)
    assert failed_run is not None
    assert failed_run.status == EvalRunStatus.FAILED.value
    assert failed_run.completed_at is not None
    assert failed_run.completed_cases == 0
    assert failed_run.error_count == 0
    factory.assert_not_called()


def test_provider_factory_failure_persists_failed_run_and_raises(db: Session) -> None:
    dataset, prompt, model_config, _ = seed_configuration(db)

    def failing_factory(_: ModelConfig) -> FakeProvider:
        raise ValueError("provider configuration is invalid")

    with pytest.raises(EvalRunSetupError) as exc_info:
        EvalRunner(db, provider_factory=failing_factory).run(dataset.id, prompt.id, model_config.id)

    assert exc_info.value.run_id is not None
    assert "provider configuration is invalid" in str(exc_info.value)
    failed_run = db.get(EvalRun, exc_info.value.run_id)
    assert failed_run is not None
    assert failed_run.status == EvalRunStatus.FAILED.value
    assert failed_run.completed_at is not None


def test_default_provider_factory_supports_only_openai(monkeypatch) -> None:
    expected_provider = FakeProvider([])
    provider_constructor = Mock(return_value=expected_provider)
    monkeypatch.setattr("app.services.eval_runner.OpenAIProvider", provider_constructor)
    openai_config = ModelConfig(
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=None,
        max_output_tokens=128,
        response_format=None,
    )
    unsupported_config = ModelConfig(
        provider="unsupported",
        model_name="example-model",
        temperature=None,
        max_output_tokens=128,
        response_format=None,
    )

    assert default_provider_factory(openai_config) is expected_provider
    provider_constructor.assert_called_once_with()
    with pytest.raises(ValueError, match="Unsupported model provider: unsupported"):
        default_provider_factory(unsupported_config)


def test_empty_dataset_completes_with_zero_counts(db: Session) -> None:
    dataset, prompt, model_config, _ = seed_configuration(db, case_inputs=[])
    provider = FakeProvider([])

    eval_run = EvalRunner(db, provider_factory=lambda _: provider).run(
        dataset.id,
        prompt.id,
        model_config.id,
    )

    assert eval_run.status == EvalRunStatus.COMPLETED.value
    assert eval_run.total_cases == 0
    assert eval_run.completed_cases == 0
    assert eval_run.error_count == 0
    assert eval_run.failed_count == 0
    assert eval_run.pass_rate is None
    assert eval_run.avg_score is None
    assert eval_run.completed_at is not None
    assert db.scalar(select(func.count(EvalResult.id))) == 0
    assert provider.requests == []
