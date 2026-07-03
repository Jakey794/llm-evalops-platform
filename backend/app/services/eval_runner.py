import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import (
    Dataset,
    EvalResult,
    EvalRun,
    EvalRunStatus,
    ModelConfig,
    ModelProvider,
    PromptVersion,
    TestCase,
)
from app.services.cost_tracker import estimate_cost_usd
from app.services.metrics import calculate_run_metrics
from app.services.prompt_renderer import render_prompt
from app.services.providers import LLMProvider, LLMRequest, LLMResponse, OpenAIProvider

ProviderFactory = Callable[[ModelConfig], LLMProvider]


class EvalRunnerError(RuntimeError):
    """Base exception for run-level evaluation failures."""


class EvalResourceNotFoundError(EvalRunnerError):
    def __init__(self, resource_type: str, resource_id: uuid.UUID) -> None:
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} not found: {resource_id}")


class EvalRunSetupError(EvalRunnerError):
    def __init__(self, message: str, *, run_id: uuid.UUID | None = None) -> None:
        self.run_id = run_id
        suffix = f" (run_id={run_id})" if run_id is not None else ""
        super().__init__(f"{message}{suffix}")


def default_provider_factory(model_config: ModelConfig) -> LLMProvider:
    if model_config.provider == ModelProvider.OPENAI.value:
        return OpenAIProvider()
    raise ValueError(f"Unsupported model provider: {model_config.provider}")


class EvalRunner:
    def __init__(
        self,
        session: Session,
        provider_factory: ProviderFactory = default_provider_factory,
    ) -> None:
        self._session = session
        self._provider_factory = provider_factory

    def run(
        self,
        dataset_id: uuid.UUID,
        prompt_version_id: uuid.UUID,
        model_config_id: uuid.UUID,
    ) -> EvalRun:
        dataset = self._get_required(Dataset, dataset_id, "Dataset")
        prompt_version = self._get_required(
            PromptVersion,
            prompt_version_id,
            "PromptVersion",
        )
        model_config = self._get_required(ModelConfig, model_config_id, "ModelConfig")
        test_cases = list(
            self._session.scalars(
                select(TestCase)
                .where(TestCase.dataset_id == dataset.id)
                .order_by(TestCase.created_at, TestCase.id)
            )
        )

        eval_run = EvalRun(
            dataset_id=dataset.id,
            prompt_version_id=prompt_version.id,
            model_config_id=model_config.id,
            status=EvalRunStatus.RUNNING.value,
            started_at=_utcnow(),
            total_cases=len(test_cases),
            completed_cases=0,
            error_count=0,
        )
        self._session.add(eval_run)
        try:
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise EvalRunSetupError("Failed to create eval run") from exc
        run_id = eval_run.id

        try:
            self._validate_workflow(dataset, prompt_version)
            provider = self._provider_factory(model_config)
            if not isinstance(provider, LLMProvider):
                raise TypeError("Provider factory did not return an LLMProvider")
        except Exception as exc:
            self._mark_failed(run_id)
            raise EvalRunSetupError(str(exc), run_id=run_id) from exc

        for test_case in test_cases:
            result = self._process_case(
                eval_run=eval_run,
                test_case=test_case,
                prompt_version=prompt_version,
                model_config=model_config,
                provider=provider,
            )
            self._session.add(result)
            eval_run.completed_cases += 1
            if result.error is not None:
                eval_run.error_count += 1

            try:
                self._session.commit()
            except SQLAlchemyError as exc:
                self._session.rollback()
                self._mark_failed(run_id)
                raise EvalRunSetupError(
                    "Failed to persist eval result",
                    run_id=run_id,
                ) from exc

        try:
            persisted_results = list(
                self._session.scalars(select(EvalResult).where(EvalResult.eval_run_id == run_id))
            )
            metrics = calculate_run_metrics(persisted_results)
            eval_run.completed_cases = metrics.completed_cases
            eval_run.error_count = metrics.error_count
            eval_run.total_cost_usd = metrics.total_cost_usd
            eval_run.avg_latency_ms = metrics.avg_latency_ms
            eval_run.p95_latency_ms = metrics.p95_latency_ms
            eval_run.status = EvalRunStatus.COMPLETED.value
            eval_run.completed_at = _utcnow()
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            self._mark_failed(run_id)
            raise EvalRunSetupError(
                "Failed to complete eval run",
                run_id=run_id,
            ) from exc

        return eval_run

    def _get_required(
        self,
        model_type: type[Dataset] | type[PromptVersion] | type[ModelConfig],
        resource_id: uuid.UUID,
        resource_type: str,
    ) -> Dataset | PromptVersion | ModelConfig:
        resource = self._session.get(model_type, resource_id)
        if resource is None:
            raise EvalResourceNotFoundError(resource_type, resource_id)
        return resource

    @staticmethod
    def _validate_workflow(dataset: Dataset, prompt_version: PromptVersion) -> None:
        if dataset.workflow_type != prompt_version.workflow_type:
            raise ValueError(
                "Dataset and prompt version workflow types do not match: "
                f"{dataset.workflow_type!r} != {prompt_version.workflow_type!r}"
            )

    @staticmethod
    def _process_case(
        *,
        eval_run: EvalRun,
        test_case: TestCase,
        prompt_version: PromptVersion,
        model_config: ModelConfig,
        provider: LLMProvider,
    ) -> EvalResult:
        try:
            rendered_prompt = render_prompt(prompt_version.template, test_case.input_json)
            response = provider.generate(
                LLMRequest(
                    prompt=rendered_prompt,
                    model_name=model_config.model_name,
                    temperature=model_config.temperature,
                    max_output_tokens=model_config.max_output_tokens,
                    response_format=model_config.response_format,
                    metadata={
                        "eval_run_id": str(eval_run.id),
                        "test_case_id": str(test_case.id),
                        "test_case_external_id": test_case.external_id,
                    },
                )
            )
        except Exception as exc:
            response = LLMResponse(
                text=None,
                parsed_json=None,
                latency_ms=0,
                input_tokens=None,
                output_tokens=None,
                model_name=model_config.model_name,
                raw_response=None,
                error=f"{type(exc).__name__}: {exc}",
            )

        return EvalResult(
            eval_run_id=eval_run.id,
            test_case_id=test_case.id,
            model_output=response.text,
            parsed_output=response.parsed_json,
            raw_response=response.raw_response,
            latency_ms=response.latency_ms,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            estimated_cost_usd=estimate_cost_usd(
                response.model_name,
                response.input_tokens,
                response.output_tokens,
            ),
            error=response.error,
        )

    def _mark_failed(self, run_id: uuid.UUID) -> None:
        self._session.rollback()
        try:
            eval_run = self._session.get(EvalRun, run_id)
            if eval_run is None:
                return
            eval_run.status = EvalRunStatus.FAILED.value
            eval_run.completed_at = _utcnow()
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()


def _utcnow() -> datetime:
    return datetime.now(UTC)
