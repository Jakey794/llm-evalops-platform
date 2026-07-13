import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.graders import CompositeGrader, GraderInput, GraderResult, get_rubric
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
from app.models.grader_result import GraderResult as GraderResultModel
from app.services.cost_tracker import estimate_cost_usd
from app.services.judge_provider import JudgeProviderResult, judge_output
from app.services.metrics import calculate_run_metrics
from app.services.prompt_renderer import render_prompt
from app.services.providers import LLMProvider, LLMRequest, LLMResponse, OpenAIProvider

ProviderFactory = Callable[[ModelConfig], LLMProvider]
JudgeFunction = Callable[..., JudgeProviderResult]

COMPOSITE_SCORE_WEIGHTS: dict[str, tuple[float, float]] = {
    "support_classification": (0.7, 0.3),
    "incident_triage": (0.4, 0.6),
}
FALLBACK_COMPOSITE_WEIGHTS = (0.5, 0.5)


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
        judge_function: JudgeFunction = judge_output,
        judge_enabled: bool | None = None,
    ) -> None:
        self._session = session
        self._provider_factory = provider_factory
        self._judge_function = judge_function
        self._judge_enabled = (
            get_settings().llm_judge_enabled if judge_enabled is None else judge_enabled
        )

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
            eval_run.pass_rate = metrics.pass_rate
            eval_run.avg_score = metrics.avg_score
            eval_run.failed_count = metrics.failed_count
            eval_run.total_cases = metrics.total_count
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

    def _process_case(
        self,
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

        parsed_output = response.parsed_json
        if parsed_output is None:
            parsed_output = _parse_json(response.text)
        grader_config = _resolve_grader_config(test_case)
        model_output_for_grading = (
            response.text
            if response.text is not None
            else parsed_output
            if isinstance(parsed_output, dict)
            else None
        )
        deterministic_result = CompositeGrader().grade(
            GraderInput(
                test_case_id=str(test_case.id),
                workflow_type=test_case.workflow_type,
                input_data=test_case.input_json,
                expected_output=test_case.expected_output_json,
                model_output=model_output_for_grading,
                parsed_output=parsed_output if isinstance(parsed_output, dict) else None,
                grader_config=grader_config,
                tags=test_case.tags,
                difficulty=test_case.difficulty,
            )
        )
        if response.error is not None:
            deterministic_result = _provider_error_result(deterministic_result, response.error)

        primary_cost = estimate_cost_usd(
            response.model_name,
            response.input_tokens,
            response.output_tokens,
        )
        eval_result = EvalResult(
            eval_run_id=eval_run.id,
            test_case_id=test_case.id,
            model_output=response.text,
            parsed_output=parsed_output,
            raw_response=response.raw_response,
            latency_ms=response.latency_ms,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            estimated_cost_usd=primary_cost,
            error=response.error,
            score=deterministic_result.score,
            passed=deterministic_result.passed,
            grader_feedback=deterministic_result.feedback,
            failure_modes=deterministic_result.failure_modes,
            grader_breakdown=deterministic_result.metadata,
        )
        eval_result.grader_results.extend(_deterministic_grader_rows(deterministic_result))

        if _judge_is_enabled(grader_config, default=self._judge_enabled):
            judge_result = self._evaluate_with_judge(
                workflow_type=test_case.workflow_type,
                input_json=test_case.input_json,
                expected_output_json=test_case.expected_output_json,
                model_output=model_output_for_grading,
                deterministic_result=deterministic_result,
            )
            eval_result.grader_results.append(_judge_grader_row(judge_result))
            _apply_judge_result(
                eval_result=eval_result,
                deterministic_result=deterministic_result,
                judge_result=judge_result,
                workflow_type=test_case.workflow_type,
            )
            judge_cost = _judge_cost(judge_result)
            eval_result.estimated_cost_usd = _combine_costs(primary_cost, judge_cost)

        return eval_result

    def _evaluate_with_judge(
        self,
        *,
        workflow_type: str,
        input_json: dict[str, Any],
        expected_output_json: dict[str, Any],
        model_output: Any,
        deterministic_result: GraderResult,
    ) -> JudgeProviderResult:
        try:
            return self._judge_function(
                workflow_type=workflow_type,
                input_json=input_json,
                expected_output_json=expected_output_json,
                model_output=model_output,
                deterministic_summary=deterministic_result.model_dump(mode="json"),
            )
        except Exception as exc:
            return JudgeProviderResult(
                judge_output=None,
                usage=None,
                latency_ms=0,
                model_name=get_settings().llm_judge_model,
                raw_output=None,
                error=f"LLM judge integration error: {type(exc).__name__}: {exc}",
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


def _parse_json(value: str | None) -> dict[str, object] | list[object] | None:
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, (dict, list)) else None


def _resolve_grader_config(test_case: TestCase) -> dict[str, object]:
    configured = test_case.metadata_json.get("grader_config")
    if isinstance(configured, dict) and configured:
        return configured

    expected = test_case.expected_output_json
    exact_fields = list(expected)
    return {
        "json_schema": {
            "required_fields": exact_fields,
            "field_types": {field: _json_type_name(value) for field, value in expected.items()},
            "allow_extra_fields": False,
        },
        "exact_match": {"exact_fields": exact_fields},
    }


def _json_type_name(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    return "object"


def _judge_is_enabled(grader_config: dict[str, object], *, default: bool) -> bool:
    direct_setting = grader_config.get("llm_judge_enabled")
    if isinstance(direct_setting, bool):
        return direct_setting

    judge_config = grader_config.get("llm_judge")
    if isinstance(judge_config, bool):
        return judge_config
    if isinstance(judge_config, dict):
        configured = judge_config.get("enabled")
        if isinstance(configured, bool):
            return configured
    return default


def _deterministic_grader_rows(result: GraderResult) -> list[GraderResultModel]:
    raw_components = result.metadata.get("grader_results")
    if not isinstance(raw_components, list):
        return []

    rows: list[GraderResultModel] = []
    for raw_component in raw_components:
        component = GraderResult.model_validate(raw_component)
        rows.append(
            GraderResultModel(
                grader_name=component.grader_name,
                grader_type="deterministic",
                score=component.score,
                passed=component.passed,
                feedback=component.feedback,
                failure_modes=component.failure_modes,
                rubric_scores={},
                raw_output=component.metadata,
                error=None,
            )
        )
    return rows


def _judge_grader_row(result: JudgeProviderResult) -> GraderResultModel:
    output = result.judge_output
    judge_cost = _judge_cost(result)
    provider_metadata: dict[str, Any] = {
        "model_name": result.model_name,
        "latency_ms": result.latency_ms,
        "usage": result.usage.model_dump(mode="json") if result.usage is not None else None,
        "estimated_cost_usd": str(judge_cost) if judge_cost is not None else None,
        "response": result.raw_output,
    }
    return GraderResultModel(
        grader_name="llm_judge",
        grader_type="llm",
        score=output.score if output is not None else None,
        passed=output.passed if output is not None else None,
        feedback=output.reason if output is not None else None,
        failure_modes=output.failure_modes if output is not None else [],
        rubric_scores=output.rubric_scores if output is not None else {},
        raw_output=provider_metadata,
        error=result.error,
    )


def _apply_judge_result(
    *,
    eval_result: EvalResult,
    deterministic_result: GraderResult,
    judge_result: JudgeProviderResult,
    workflow_type: str,
) -> None:
    judge_output = judge_result.judge_output
    metadata = dict(deterministic_result.metadata)

    if judge_result.error is not None or judge_output is None:
        metadata["llm_judge"] = {
            "error": judge_result.error or "Judge output was unavailable",
            "latency_ms": judge_result.latency_ms,
            "model_name": judge_result.model_name,
        }
        eval_result.grader_feedback = (
            f"{deterministic_result.feedback} "
            f"LLM judge error: {judge_result.error or 'Judge output was unavailable'}."
        )
        eval_result.grader_breakdown = metadata
        return

    deterministic_weight, judge_weight = COMPOSITE_SCORE_WEIGHTS.get(
        workflow_type,
        FALLBACK_COMPOSITE_WEIGHTS,
    )
    final_score = max(
        0.0,
        min(
            1.0,
            deterministic_result.score * deterministic_weight + judge_output.score * judge_weight,
        ),
    )
    pass_threshold = get_rubric(workflow_type).pass_threshold
    breakdown = metadata.get("breakdown")
    metadata["breakdown"] = {
        **(breakdown if isinstance(breakdown, dict) else {}),
        "llm_judge": judge_output.score,
    }
    metadata["llm_judge"] = judge_output.model_dump(mode="json")
    metadata["composite"] = {
        "deterministic_score": deterministic_result.score,
        "deterministic_weight": deterministic_weight,
        "llm_judge_score": judge_output.score,
        "llm_judge_weight": judge_weight,
        "pass_threshold": pass_threshold,
        "score": final_score,
    }

    eval_result.score = final_score
    eval_result.passed = final_score >= pass_threshold
    eval_result.grader_feedback = (
        f"Composite score {final_score:.3f} with pass threshold {pass_threshold:.3f}. "
        f"Deterministic score {deterministic_result.score:.3f}. "
        f"LLM judge: {judge_output.reason}"
    )
    eval_result.failure_modes = list(
        dict.fromkeys([*deterministic_result.failure_modes, *judge_output.failure_modes])
    )
    eval_result.grader_breakdown = metadata


def _judge_cost(result: JudgeProviderResult) -> Decimal | None:
    if result.usage is None:
        return None
    return estimate_cost_usd(
        result.model_name,
        result.usage.input_tokens,
        result.usage.output_tokens,
    )


def _combine_costs(primary: Decimal | None, judge: Decimal | None) -> Decimal | None:
    costs = [cost for cost in (primary, judge) if cost is not None]
    return sum(costs, start=Decimal("0")) if costs else None


def _provider_error_result(result: GraderResult, error: str) -> GraderResult:
    failure_modes = list(dict.fromkeys(["provider_error", *result.failure_modes]))
    return GraderResult(
        grader_name=result.grader_name,
        score=0.0,
        passed=False,
        feedback=f"Provider error: {error}. {result.feedback}",
        failure_modes=failure_modes,
        metadata=result.metadata | {"provider_error": error},
    )
