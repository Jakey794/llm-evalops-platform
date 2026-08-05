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
    dataset_id: str | None = None
    prompt_version_id: str | None = None
    model_config_id: str | None = None
    mock_profile: str | None = None
    error: str | None = None


MOCK_PROFILE_EXPECTED = "expected"
MOCK_PROFILE_DEGRADED = "degraded"
MOCK_PROFILES = (MOCK_PROFILE_EXPECTED, MOCK_PROFILE_DEGRADED)


class ExpectedOutputMockProvider:
    """Deterministic provider for CI: returns the case expected output as JSON."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def generate(self, request: LLMRequest) -> LLMResponse:
        test_case = _load_test_case(self._session, request)
        payload = test_case.expected_output_json if test_case is not None else {"ok": True}
        return _mock_response(
            request,
            payload if isinstance(payload, dict) else {"ok": True},
            provider="expected_output",
        )


class DegradedOutputMockProvider:
    """Deterministic provider that returns controlled wrong outputs for regression gates."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def generate(self, request: LLMRequest) -> LLMResponse:
        test_case = _load_test_case(self._session, request)
        expected = test_case.expected_output_json if test_case is not None else {}
        payload = _degraded_payload(expected if isinstance(expected, dict) else {})
        return _mock_response(request, payload, provider="degraded_output", latency_ms=18)


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
    parser.add_argument(
        "--mock-profile",
        choices=MOCK_PROFILES,
        default=None,
        help=(
            "Mock output profile: 'expected' mirrors expected outputs (pass path); "
            "'degraded' returns controlled wrong outputs (threshold-failure path). "
            "Defaults to EVAL_GATE_MOCK_PROFILE or 'expected' when --mock is set."
        ),
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
    mock_profile: str | None = None,
) -> GateReport:
    resolved_profile = _resolve_mock_profile(mock=mock, mock_profile=mock_profile)
    identifiers = {
        "dataset_id": str(dataset_id),
        "prompt_version_id": str(prompt_version_id),
        "model_config_id": str(model_config_id),
        "mock_profile": resolved_profile,
    }
    factory = provider_factory
    if factory is None:
        if mock or _env_flag("EVAL_GATE_MOCK") or resolved_profile is not None:
            factory = _mock_provider_factory(
                session, profile=resolved_profile or MOCK_PROFILE_EXPECTED
            )
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
            **identifiers,
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
        **identifiers,
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

    try:
        _resolve_mock_profile(mock=bool(args.mock), mock_profile=args.mock_profile)
    except ValueError as exc:
        _print_error(str(exc))
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
                mock_profile=args.mock_profile,
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


def _mock_provider_factory(session: Session, *, profile: str) -> ProviderFactory:
    if profile == MOCK_PROFILE_DEGRADED:
        provider: LLMProvider = DegradedOutputMockProvider(session)
    elif profile == MOCK_PROFILE_EXPECTED:
        provider = ExpectedOutputMockProvider(session)
    else:
        raise ValueError(f"Unknown mock profile: {profile}")

    def factory(_model_config: ModelConfig) -> LLMProvider:
        return provider

    return factory


def _resolve_mock_profile(*, mock: bool, mock_profile: str | None) -> str | None:
    if mock_profile is not None:
        return mock_profile
    env_profile = os.getenv("EVAL_GATE_MOCK_PROFILE", "").strip().lower()
    if env_profile:
        if env_profile not in MOCK_PROFILES:
            raise ValueError(
                f"Invalid EVAL_GATE_MOCK_PROFILE={env_profile!r}; "
                f"expected one of {', '.join(MOCK_PROFILES)}"
            )
        return env_profile
    if mock or _env_flag("EVAL_GATE_MOCK"):
        return MOCK_PROFILE_EXPECTED
    return None


def _load_test_case(session: Session, request: LLMRequest):
    from app.models import TestCase

    test_case_id = (request.metadata or {}).get("test_case_id")
    if not isinstance(test_case_id, str):
        return None
    try:
        return session.get(TestCase, uuid.UUID(test_case_id))
    except ValueError:
        return None


def _mock_response(
    request: LLMRequest,
    payload: dict[str, Any],
    *,
    provider: str,
    latency_ms: int = 12,
) -> LLMResponse:
    text = json.dumps(payload)
    return LLMResponse(
        text=text,
        parsed_json=payload,
        latency_ms=latency_ms,
        input_tokens=20,
        output_tokens=10,
        model_name=request.model_name,
        raw_response={"mock": True, "provider": provider},
        error=None,
    )


def _degraded_payload(expected: dict[str, Any]) -> dict[str, Any]:
    """Build a schema-shaped but intentionally incorrect payload for regression demos."""
    if "citations" in expected or "answer" in expected:
        return {
            "answer": "This is a speculative answer with invented details and no citations.",
            "citations": [],
        }
    if "category" in expected:
        return {
            "category": "technical_support",
            "priority": "low",
            "routed_team": "general",
        }
    if "severity" in expected:
        return {
            "severity": "sev-1",
            "impacted_service": "unknown",
            "likely_root_cause": "unclear",
            "summary": "Speculative triage with insufficient evidence.",
        }
    return {"degraded": True, "ok": False}


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
