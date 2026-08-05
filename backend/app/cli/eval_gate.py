"""CI eval gate: run an evaluation and enforce quality/cost/latency thresholds."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session_factory
from app.models import Dataset, EvalRun, ModelConfig, PromptVersion
from app.services.eval_runner import EvalRunner, ProviderFactory, default_provider_factory
from app.services.providers import LLMProvider, LLMRequest, LLMResponse

EXIT_PASS = 0
EXIT_THRESHOLD_FAILURE = 1
EXIT_CONFIG_ERROR = 2
EXIT_RUNTIME_ERROR = 3


@dataclass(frozen=True, slots=True)
class GateThresholds:
    min_pass_rate: float | None
    min_avg_score: float | None
    max_cost_usd: float | None
    max_p95_latency_ms: float | None


@dataclass(frozen=True, slots=True)
class GateViolation:
    metric: str
    actual: float | None
    limit: float
    comparison: str


@dataclass(frozen=True, slots=True)
class GateReport:
    passed: bool
    exit_code: int
    eval_run_id: str | None
    status: str | None
    metrics: dict[str, Any]
    thresholds: dict[str, float | None]
    violations: list[dict[str, Any]]
    error: str | None = None


class ExpectedOutputMockProvider:
    """Deterministic provider for CI: returns the case expected output as JSON."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def generate(self, request: LLMRequest) -> LLMResponse:
        from app.models import TestCase

        test_case_id = (request.metadata or {}).get("test_case_id")
        test_case = None
        if isinstance(test_case_id, str):
            try:
                test_case = self._session.get(TestCase, uuid.UUID(test_case_id))
            except ValueError:
                test_case = None

        payload = test_case.expected_output_json if test_case is not None else {"ok": True}
        text = json.dumps(payload)
        return LLMResponse(
            text=text,
            parsed_json=payload if isinstance(payload, dict) else None,
            latency_ms=12,
            input_tokens=20,
            output_tokens=10,
            model_name=request.model_name,
            raw_response={"mock": True, "provider": "expected_output"},
            error=None,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval-gate",
        description="Run an eval and fail if quality, cost, or latency thresholds are breached.",
    )
    parser.add_argument("--dataset-id", help="Dataset UUID")
    parser.add_argument("--dataset-name", help="Dataset name (alternative to --dataset-id)")
    parser.add_argument("--prompt-version-id", help="Prompt version UUID")
    parser.add_argument("--prompt-name", help="Prompt version name")
    parser.add_argument("--prompt-version-label", default="v1", help="Prompt version label")
    parser.add_argument("--model-config-id", help="Model config UUID")
    parser.add_argument("--model-name", help="Model config model_name (latest match)")
    parser.add_argument("--min-pass-rate", type=float, default=None)
    parser.add_argument("--min-avg-score", type=float, default=None)
    parser.add_argument("--max-cost-usd", type=float, default=None)
    parser.add_argument("--max-p95-latency-ms", type=float, default=None)
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("eval-gate-report.json"),
        help="Where to write the JSON report",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use deterministic mock provider (no external API calls).",
    )
    return parser


def evaluate_thresholds(
    eval_run: EvalRun,
    thresholds: GateThresholds,
) -> list[GateViolation]:
    violations: list[GateViolation] = []
    if thresholds.min_pass_rate is not None:
        actual = eval_run.pass_rate
        if actual is None or actual < thresholds.min_pass_rate:
            violations.append(
                GateViolation(
                    metric="pass_rate",
                    actual=actual,
                    limit=thresholds.min_pass_rate,
                    comparison=">=",
                )
            )
    if thresholds.min_avg_score is not None:
        actual = eval_run.avg_score
        if actual is None or actual < thresholds.min_avg_score:
            violations.append(
                GateViolation(
                    metric="avg_score",
                    actual=actual,
                    limit=thresholds.min_avg_score,
                    comparison=">=",
                )
            )
    if thresholds.max_cost_usd is not None:
        actual = float(eval_run.total_cost_usd or Decimal("0"))
        if actual > thresholds.max_cost_usd:
            violations.append(
                GateViolation(
                    metric="total_cost_usd",
                    actual=actual,
                    limit=thresholds.max_cost_usd,
                    comparison="<=",
                )
            )
    if thresholds.max_p95_latency_ms is not None:
        actual = eval_run.p95_latency_ms
        if actual is None or actual > thresholds.max_p95_latency_ms:
            violations.append(
                GateViolation(
                    metric="p95_latency_ms",
                    actual=actual,
                    limit=thresholds.max_p95_latency_ms,
                    comparison="<=",
                )
            )
    return violations


def resolve_resources(
    session: Session,
    *,
    dataset_id: str | None,
    dataset_name: str | None,
    prompt_version_id: str | None,
    prompt_name: str | None,
    prompt_version_label: str,
    model_config_id: str | None,
    model_name: str | None,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    dataset = _resolve_dataset(session, dataset_id=dataset_id, dataset_name=dataset_name)
    prompt = _resolve_prompt(
        session,
        prompt_version_id=prompt_version_id,
        prompt_name=prompt_name,
        version_label=prompt_version_label,
        workflow_type=dataset.workflow_type,
    )
    model = _resolve_model(session, model_config_id=model_config_id, model_name=model_name)
    return dataset.id, prompt.id, model.id


def run_gate(
    *,
    session: Session,
    dataset_id: uuid.UUID,
    prompt_version_id: uuid.UUID,
    model_config_id: uuid.UUID,
    thresholds: GateThresholds,
    provider_factory: ProviderFactory | None = None,
    mock: bool = False,
) -> GateReport:
    factory = provider_factory
    if factory is None:
        if mock or _env_flag("EVAL_GATE_MOCK"):
            factory = _mock_provider_factory(session)
        else:
            factory = default_provider_factory

    try:
        eval_run = EvalRunner(session, provider_factory=factory, judge_enabled=False).run(
            dataset_id=dataset_id,
            prompt_version_id=prompt_version_id,
            model_config_id=model_config_id,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary converts to exit code
        return GateReport(
            passed=False,
            exit_code=EXIT_RUNTIME_ERROR,
            eval_run_id=None,
            status=None,
            metrics={},
            thresholds=asdict(thresholds),
            violations=[],
            error=f"{type(exc).__name__}: {exc}",
        )

    violations = evaluate_thresholds(eval_run, thresholds)
    passed = not violations and eval_run.status == "completed"
    return GateReport(
        passed=passed,
        exit_code=EXIT_PASS if passed else EXIT_THRESHOLD_FAILURE,
        eval_run_id=str(eval_run.id),
        status=eval_run.status,
        metrics={
            "pass_rate": eval_run.pass_rate,
            "avg_score": eval_run.avg_score,
            "total_cost_usd": float(eval_run.total_cost_usd or 0),
            "avg_latency_ms": eval_run.avg_latency_ms,
            "p95_latency_ms": eval_run.p95_latency_ms,
            "failed_count": eval_run.failed_count,
            "total_count": eval_run.total_cases,
            "error_count": eval_run.error_count,
        },
        thresholds=asdict(thresholds),
        violations=[asdict(item) for item in violations],
    )


def write_report(report: GateReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    thresholds = GateThresholds(
        min_pass_rate=args.min_pass_rate,
        min_avg_score=args.min_avg_score,
        max_cost_usd=args.max_cost_usd,
        max_p95_latency_ms=args.max_p95_latency_ms,
    )
    if all(value is None for value in asdict(thresholds).values()):
        _print_error("At least one threshold flag is required.")
        return EXIT_CONFIG_ERROR

    session_factory = get_session_factory()
    try:
        with session_factory() as session:
            try:
                dataset_id, prompt_id, model_id = resolve_resources(
                    session,
                    dataset_id=args.dataset_id,
                    dataset_name=args.dataset_name,
                    prompt_version_id=args.prompt_version_id,
                    prompt_name=args.prompt_name,
                    prompt_version_label=args.prompt_version_label,
                    model_config_id=args.model_config_id,
                    model_name=args.model_name,
                )
            except ValueError as exc:
                report = GateReport(
                    passed=False,
                    exit_code=EXIT_CONFIG_ERROR,
                    eval_run_id=None,
                    status=None,
                    metrics={},
                    thresholds=asdict(thresholds),
                    violations=[],
                    error=str(exc),
                )
                write_report(report, args.report_path)
                _print_error(str(exc))
                return EXIT_CONFIG_ERROR

            report = run_gate(
                session=session,
                dataset_id=dataset_id,
                prompt_version_id=prompt_id,
                model_config_id=model_id,
                thresholds=thresholds,
                mock=bool(args.mock),
            )
    except Exception as exc:  # noqa: BLE001
        report = GateReport(
            passed=False,
            exit_code=EXIT_RUNTIME_ERROR,
            eval_run_id=None,
            status=None,
            metrics={},
            thresholds=asdict(thresholds),
            violations=[],
            error=f"{type(exc).__name__}: {exc}",
        )
        write_report(report, args.report_path)
        _print_error(report.error or "Eval gate failed")
        return EXIT_RUNTIME_ERROR

    write_report(report, args.report_path)
    if report.error:
        _print_error(report.error)
    elif report.passed:
        print(f"Eval gate passed (run_id={report.eval_run_id})")
    else:
        print(f"Eval gate failed (run_id={report.eval_run_id})")
        for violation in report.violations:
            print(
                f"  - {violation['metric']}: actual={violation['actual']} "
                f"required {violation['comparison']} {violation['limit']}"
            )
    return report.exit_code


def _resolve_dataset(
    session: Session,
    *,
    dataset_id: str | None,
    dataset_name: str | None,
) -> Dataset:
    if dataset_id:
        dataset = session.get(Dataset, uuid.UUID(dataset_id))
        if dataset is None:
            raise ValueError(f"Dataset not found: {dataset_id}")
        return dataset
    if dataset_name:
        dataset = session.scalars(select(Dataset).where(Dataset.name == dataset_name)).first()
        if dataset is None:
            raise ValueError(f"Dataset not found by name: {dataset_name}")
        return dataset
    raise ValueError("Provide --dataset-id or --dataset-name")


def _resolve_prompt(
    session: Session,
    *,
    prompt_version_id: str | None,
    prompt_name: str | None,
    version_label: str,
    workflow_type: str,
) -> PromptVersion:
    if prompt_version_id:
        prompt = session.get(PromptVersion, uuid.UUID(prompt_version_id))
        if prompt is None:
            raise ValueError(f"Prompt version not found: {prompt_version_id}")
        return prompt
    if prompt_name:
        prompt = session.scalars(
            select(PromptVersion).where(
                PromptVersion.name == prompt_name,
                PromptVersion.version_label == version_label,
                PromptVersion.workflow_type == workflow_type,
            )
        ).first()
        if prompt is None:
            raise ValueError(
                f"Prompt version not found: name={prompt_name!r} "
                f"label={version_label!r} workflow={workflow_type!r}"
            )
        return prompt
    raise ValueError("Provide --prompt-version-id or --prompt-name")


def _resolve_model(
    session: Session,
    *,
    model_config_id: str | None,
    model_name: str | None,
) -> ModelConfig:
    if model_config_id:
        model = session.get(ModelConfig, uuid.UUID(model_config_id))
        if model is None:
            raise ValueError(f"Model config not found: {model_config_id}")
        return model
    if model_name:
        model = session.scalars(
            select(ModelConfig)
            .where(ModelConfig.model_name == model_name)
            .order_by(ModelConfig.created_at.desc())
        ).first()
        if model is None:
            raise ValueError(f"Model config not found by model_name: {model_name}")
        return model
    raise ValueError("Provide --model-config-id or --model-name")


def _mock_provider_factory(session: Session) -> ProviderFactory:
    provider: LLMProvider = ExpectedOutputMockProvider(session)

    def factory(_model_config: ModelConfig) -> LLMProvider:
        return provider

    return factory


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
