from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from math import ceil

from app.models import EvalResult


@dataclass(frozen=True, slots=True)
class EvalRunMetrics:
    total_cost_usd: Decimal
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    error_count: int
    completed_cases: int
    pass_rate: float | None
    avg_score: float | None
    failed_count: int
    total_count: int


def calculate_run_metrics(results: Iterable[EvalResult]) -> EvalRunMetrics:
    result_list = list(results)
    scores = [float(result.score) for result in result_list if result.score is not None]
    passed_count = sum(result.passed is True for result in result_list)
    failed_count = sum(result.passed is False for result in result_list)
    total_count = len(result_list)
    latencies = sorted(
        float(result.latency_ms) for result in result_list if result.latency_ms is not None
    )

    avg_latency_ms = sum(latencies) / len(latencies) if latencies else None
    p95_latency_ms = latencies[ceil(0.95 * len(latencies)) - 1] if latencies else None

    return EvalRunMetrics(
        total_cost_usd=sum(
            (
                result.estimated_cost_usd
                for result in result_list
                if result.estimated_cost_usd is not None
            ),
            start=Decimal("0"),
        ),
        avg_latency_ms=avg_latency_ms,
        p95_latency_ms=p95_latency_ms,
        error_count=sum(result.error is not None for result in result_list),
        completed_cases=total_count,
        pass_rate=passed_count / total_count if total_count else None,
        avg_score=sum(scores) / len(scores) if scores else None,
        failed_count=failed_count,
        total_count=total_count,
    )
