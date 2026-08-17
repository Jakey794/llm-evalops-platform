import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.eval_runs import get_provider_factory
from app.db import get_db
from app.main import create_app
from app.models import (
    Base,
    Dataset,
    EvalResult,
    EvalRun,
    GraderResult,
    ModelConfig,
    PromptVersion,
)
from app.models import TestCase as CaseModel
from app.services.providers import LLMRequest, LLMResponse
from tests.conftest import OPERATOR_HEADERS


class FakeProvider:
    def generate(self, request: LLMRequest) -> LLMResponse:
        has_error = "provider-error" in request.prompt
        return LLMResponse(
            text=None if has_error else f"answer: {request.prompt}",
            parsed_json=None if has_error else {"ok": True},
            latency_ms=7,
            input_tokens=10,
            output_tokens=3,
            model_name=request.model_name,
            raw_response={"request_id": "fake-response"},
            error="fake provider failure" if has_error else None,
        )


@dataclass
class ApiContext:
    client: TestClient
    session_factory: sessionmaker[Session]
    dataset_id: uuid.UUID
    prompt_version_id: uuid.UUID
    model_config_id: uuid.UUID

    @property
    def request_body(self) -> dict[str, str]:
        return {
            "dataset_id": str(self.dataset_id),
            "prompt_version_id": str(self.prompt_version_id),
            "model_config_id": str(self.model_config_id),
        }


@pytest.fixture
def api() -> Generator[ApiContext, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with testing_session() as db:
        dataset = Dataset(
            name="API dataset",
            workflow_type="support_classification",
            test_cases=[
                CaseModel(
                    external_id="case-success",
                    input_json={"ticket": "normal"},
                    expected_output_json={"ok": True},
                    required_citations=[],
                    tags=[],
                    difficulty="easy",
                    workflow_type="support_classification",
                    metadata_json={},
                ),
                CaseModel(
                    external_id="case-error",
                    input_json={"ticket": "provider-error"},
                    expected_output_json={"ok": True},
                    required_citations=[],
                    tags=[],
                    difficulty="hard",
                    workflow_type="support_classification",
                    metadata_json={},
                ),
            ],
        )
        prompt = PromptVersion(
            name="support_api",
            workflow_type="support_classification",
            template="Classify {{ ticket }}",
            version_label="v1",
        )
        model = ModelConfig(
            provider="openai",
            model_name="fake-model",
            temperature=0,
            max_output_tokens=100,
            response_format=None,
        )
        db.add_all([dataset, prompt, model])
        db.commit()
        ids = (dataset.id, prompt.id, model.id)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as db:
            yield db

    def override_provider_factory():
        return lambda _model_config: FakeProvider()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_provider_factory] = override_provider_factory

    with TestClient(app, headers=OPERATOR_HEADERS) as client:
        yield ApiContext(client, testing_session, *ids)

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_post_runs_eval_synchronously_and_returns_completed_summary(api: ApiContext) -> None:
    response = api.client.post("/eval-runs", json=api.request_body)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["total_cases"] == 2
    assert body["completed_cases"] == 2
    assert body["error_count"] == 1
    assert body["failed_count"] == 1
    assert body["total_count"] == 2
    assert body["pass_rate"] == 0.5
    assert body["avg_score"] == 0.5
    assert body["total_cost_usd"] == "0"
    assert body["avg_latency_ms"] == 7
    assert body["p95_latency_ms"] == 7
    assert body["completed_at"] is not None

    detail_response = api.client.get(f"/eval-runs/{body['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["pass_rate"] == 0.5
    assert detail_response.json()["avg_score"] == 0.5


def test_results_and_failed_examples_are_frontend_friendly(api: ApiContext) -> None:
    run_id = api.client.post("/eval-runs", json=api.request_body).json()["id"]
    with api.session_factory() as db:
        failed_result = db.scalar(
            select(EvalResult).where(
                EvalResult.eval_run_id == uuid.UUID(run_id),
                EvalResult.error.is_not(None),
            )
        )
        assert failed_result is not None
        db.add(
            GraderResult(
                eval_result_id=failed_result.id,
                grader_name="llm_judge",
                grader_type="llm",
                score=0.2,
                passed=False,
                feedback="The response did not classify the request.",
                failure_modes=["incorrect_label"],
                rubric_scores={"category_accuracy": 0.2},
                raw_output={"model_name": "gemini-3.1-flash-lite"},
                error=None,
            )
        )
        db.commit()

    results_response = api.client.get(f"/eval-runs/{run_id}/results")
    failed_response = api.client.get(f"/eval-runs/{run_id}/failed-examples")

    assert results_response.status_code == 200
    results = results_response.json()
    assert len(results) == 2
    assert results[0]["raw_response"] == {"request_id": "fake-response"}
    assert {result["error"] for result in results} == {None, "fake provider failure"}
    assert {result["passed"] for result in results} == {True, False}
    assert {result["score"] for result in results} == {1.0, 0.0}
    assert all("grader_feedback" in result for result in results)
    assert all("failure_modes" in result for result in results)
    assert all("grader_breakdown" in result for result in results)
    assert all("grader_results" in result for result in results)
    assert all(
        {grader["grader_name"] for grader in result["grader_results"]}
        >= {"exact_match", "json_schema"}
        for result in results
    )
    failed_result_payload = next(result for result in results if result["error"] is not None)
    assert {grader["grader_name"] for grader in failed_result_payload["grader_results"]} == {
        "exact_match",
        "json_schema",
        "llm_judge",
    }

    assert failed_response.status_code == 200
    failed_examples = failed_response.json()
    assert len(failed_examples) == 1
    failed = failed_examples[0]
    assert uuid.UUID(failed["test_case_id"])
    assert failed["workflow_type"] == "support_classification"
    assert failed["difficulty"] == "hard"
    assert failed["tags"] == []
    assert failed["input_json"] == {"ticket": "provider-error"}
    assert failed["expected_output_json"] == {"ok": True}
    assert failed["model_output"] is None
    assert failed["final_score"] == 0.0
    assert failed["passed"] is False
    assert "provider_error" in failed["failure_modes"]
    assert failed["deterministic_grader_scores"] == {
        "json_schema": 0.0,
        "exact_match": 0.0,
    }
    assert failed["llm_judge_score"] == 0.2
    assert failed["judge_reason"] == "The response did not classify the request."
    assert failed["rubric_scores"] == {"category_accuracy": 0.2}
    assert failed["grader_errors"] == [
        {"grader_name": "model_provider", "error": "fake provider failure"}
    ]
    assert {grader["grader_name"] for grader in failed["grader_results"]} == {
        "exact_match",
        "json_schema",
        "llm_judge",
    }
    assert "raw_response" not in failed


def test_list_and_detail_return_runs_newest_first(api: ApiContext) -> None:
    now = datetime.now(UTC)
    with api.session_factory() as db:
        older = EvalRun(
            dataset_id=api.dataset_id,
            prompt_version_id=api.prompt_version_id,
            model_config_id=api.model_config_id,
            status="completed",
            created_at=now - timedelta(minutes=1),
        )
        newer = EvalRun(
            dataset_id=api.dataset_id,
            prompt_version_id=api.prompt_version_id,
            model_config_id=api.model_config_id,
            status="completed",
            created_at=now,
        )
        db.add_all([older, newer])
        db.commit()
        older_id, newer_id = str(older.id), str(newer.id)

    list_response = api.client.get("/eval-runs")
    detail_response = api.client.get(f"/eval-runs/{older_id}")

    assert list_response.status_code == 200
    assert [row["id"] for row in list_response.json()] == [newer_id, older_id]
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == older_id


def test_failed_examples_include_passing_result_with_judge_error(api: ApiContext) -> None:
    run_id = api.client.post("/eval-runs", json=api.request_body).json()["id"]
    with api.session_factory() as db:
        passing_result = db.scalar(
            select(EvalResult).where(
                EvalResult.eval_run_id == uuid.UUID(run_id),
                EvalResult.passed.is_(True),
            )
        )
        assert passing_result is not None
        db.add(
            GraderResult(
                eval_result_id=passing_result.id,
                grader_name="llm_judge",
                grader_type="llm",
                score=None,
                passed=None,
                feedback=None,
                failure_modes=[],
                rubric_scores={},
                raw_output={"latency_ms": 30_000},
                error="Gemini judge request timed out",
            )
        )
        db.commit()

    response = api.client.get(f"/eval-runs/{run_id}/failed-examples")

    assert response.status_code == 200
    passing_example = next(example for example in response.json() if example["passed"] is True)
    assert passing_example["final_score"] == 1.0
    assert passing_example["llm_judge_score"] is None
    assert passing_example["grader_errors"] == [
        {"grader_name": "llm_judge", "error": "Gemini judge request timed out"}
    ]


def test_missing_resources_and_runs_return_404(api: ApiContext) -> None:
    request = api.request_body | {"dataset_id": str(uuid.uuid4())}
    missing_run_id = uuid.uuid4()

    assert api.client.post("/eval-runs", json=request).status_code == 404
    assert api.client.get(f"/eval-runs/{missing_run_id}").status_code == 404
    assert api.client.get(f"/eval-runs/{missing_run_id}/results").status_code == 404
    assert api.client.get(f"/eval-runs/{missing_run_id}/failed-examples").status_code == 404


def test_setup_failure_returns_persisted_failed_run(api: ApiContext) -> None:
    with api.session_factory() as db:
        prompt = db.get(PromptVersion, api.prompt_version_id)
        assert prompt is not None
        prompt.workflow_type = "incident_triage"
        db.commit()

    response = api.client.post("/eval-runs", json=api.request_body)

    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert response.json()["completed_cases"] == 0
    assert response.json()["completed_at"] is not None


def test_post_rejects_unknown_request_fields(api: ApiContext) -> None:
    response = api.client.post("/eval-runs", json=api.request_body | {"status": "completed"})

    assert response.status_code == 422
