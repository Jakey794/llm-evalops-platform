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


def calculate_run_metrics(results: Iterable[EvalResult]) -> EvalRunMetrics:
    result_list = list(results)
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
        completed_cases=len(result_list),
    )
