import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import EvalResult, EvalRun, ModelConfig, PromptVersion
from app.models.enums import EvalRunStatus, ModelProvider
from app.schemas import (
    EvalResultCreate,
    EvalResultListItem,
    EvalResultResponse,
    EvalRunCreate,
    EvalRunResponse,
    ModelConfigCreate,
    ModelConfigListItem,
    ModelConfigResponse,
    PromptVersionCreate,
    PromptVersionListItem,
    PromptVersionResponse,
)


def test_prompt_version_schemas_serialize_orm_and_omit_template_from_list() -> None:
    prompt = PromptVersion(
        id=uuid.uuid4(),
        name="incident-triage",
        workflow_type="incident",
        template="Triage {{ title }}",
        version_label="v1",
        created_at=datetime.now(UTC),
    )

    response = PromptVersionResponse.model_validate(prompt)
    list_payload = PromptVersionListItem.model_validate(prompt).model_dump()

    assert response.template == "Triage {{ title }}"
    assert "template" not in list_payload


def test_prompt_version_create_rejects_blank_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        PromptVersionCreate(
            name="   ",
            workflow_type="incident",
            template="Triage {{ title }}",
            version_label="v1",
        )

    with pytest.raises(ValidationError):
        PromptVersionCreate(
            name="incident-triage",
            workflow_type="incident",
            template="Triage {{ title }}",
            version_label="v1",
            unsupported=True,
        )


def test_model_config_schemas_convert_provider_and_validate_limits() -> None:
    model_config = ModelConfig(
        id=uuid.uuid4(),
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=None,
        max_output_tokens=256,
        response_format={"type": "json_object"},
        created_at=datetime.now(UTC),
    )

    response = ModelConfigResponse.model_validate(model_config)
    list_payload = ModelConfigListItem.model_validate(model_config).model_dump()
    create = ModelConfigCreate(
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.2,
        max_output_tokens=256,
    )

    assert response.provider is ModelProvider.OPENAI
    assert response.response_format == {"type": "json_object"}
    assert "response_format" not in list_payload
    assert create.provider is ModelProvider.OPENAI

    with pytest.raises(ValidationError):
        ModelConfigCreate(
            provider="openai",
            model_name="gpt-4o-mini",
            temperature=2.1,
            max_output_tokens=256,
        )
    with pytest.raises(ValidationError):
        ModelConfigCreate(
            provider="openai",
            model_name="gpt-4o-mini",
            max_output_tokens=0,
        )


def test_eval_run_schemas_keep_lifecycle_fields_server_managed() -> None:
    now = datetime.now(UTC)
    eval_run = EvalRun(
        id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        prompt_version_id=uuid.uuid4(),
        model_config_id=uuid.uuid4(),
        status="pending",
        created_at=now,
        started_at=None,
        completed_at=None,
        total_cases=0,
        completed_cases=0,
        pass_rate=None,
        avg_score=None,
        total_cost_usd=Decimal("0"),
        avg_latency_ms=None,
        p95_latency_ms=None,
        error_count=0,
        failed_count=0,
    )

    response = EvalRunResponse.model_validate(eval_run)
    create = EvalRunCreate(
        dataset_id=eval_run.dataset_id,
        prompt_version_id=eval_run.prompt_version_id,
        model_config_id=eval_run.model_config_id,
    )

    assert response.status is EvalRunStatus.PENDING
    assert response.pass_rate is None
    assert response.avg_score is None
    assert response.total_cost_usd == Decimal("0")
    assert response.failed_count == 0
    assert response.total_count == 0
    assert set(create.model_dump()) == {"dataset_id", "prompt_version_id", "model_config_id"}

    with pytest.raises(ValidationError):
        EvalRunCreate(
            dataset_id=eval_run.dataset_id,
            prompt_version_id=eval_run.prompt_version_id,
            model_config_id=eval_run.model_config_id,
            status="running",
        )


def test_eval_result_schemas_serialize_json_and_validate_nonnegative_metrics() -> None:
    eval_result = EvalResult(
        id=uuid.uuid4(),
        eval_run_id=uuid.uuid4(),
        test_case_id=uuid.uuid4(),
        model_output='{"category":"billing"}',
        parsed_output={"category": "billing"},
        raw_response={"id": "response-1"},
        latency_ms=87.25,
        input_tokens=10,
        output_tokens=3,
        estimated_cost_usd=Decimal("0.00001000"),
        error=None,
        score=1.0,
        passed=True,
        grader_feedback="Matched expected output.",
        failure_modes=[],
        grader_breakdown={"breakdown": {"exact_match": 1.0}},
        created_at=datetime.now(UTC),
    )

    response = EvalResultResponse.model_validate(eval_result)
    list_payload = EvalResultListItem.model_validate(eval_result).model_dump()

    assert response.parsed_output == {"category": "billing"}
    assert response.raw_response == {"id": "response-1"}
    assert response.score == 1.0
    assert response.passed is True
    assert response.grader_breakdown == {"breakdown": {"exact_match": 1.0}}
    assert "raw_response" not in list_payload

    with pytest.raises(ValidationError):
        EvalResultCreate(
            eval_run_id=eval_result.eval_run_id,
            test_case_id=eval_result.test_case_id,
            latency_ms=-1,
        )
    with pytest.raises(ValidationError):
        EvalResultCreate(
            eval_run_id=eval_result.eval_run_id,
            test_case_id=eval_result.test_case_id,
            input_tokens=-1,
        )
