from decimal import Decimal

from app.models import EvalResult
from app.services.metrics import calculate_run_metrics


def make_result(
    *,
    latency_ms: float | None,
    cost: Decimal | None = None,
    error: str | None = None,
) -> EvalResult:
    return EvalResult(
        latency_ms=latency_ms,
        estimated_cost_usd=cost,
        error=error,
    )


def test_p95_latency_uses_nearest_rank() -> None:
    metrics = calculate_run_metrics(make_result(latency_ms=latency) for latency in range(1, 21))

    assert metrics.avg_latency_ms == 10.5
    assert metrics.p95_latency_ms == 19


def test_aggregate_metrics_include_errored_results() -> None:
    metrics = calculate_run_metrics(
        [
            make_result(latency_ms=10, cost=Decimal("0.10")),
            make_result(latency_ms=30, cost=None, error="provider failed"),
            make_result(latency_ms=None, cost=Decimal("0.25")),
        ]
    )

    assert metrics.completed_cases == 3
    assert metrics.error_count == 1
    assert metrics.total_cost_usd == Decimal("0.35")
    assert metrics.avg_latency_ms == 20
    assert metrics.p95_latency_ms == 30


def test_empty_results_have_zero_counts_and_null_latency() -> None:
    metrics = calculate_run_metrics([])

    assert metrics.completed_cases == 0
    assert metrics.error_count == 0
    assert metrics.total_cost_usd == Decimal("0")
    assert metrics.avg_latency_ms is None
    assert metrics.p95_latency_ms is None
