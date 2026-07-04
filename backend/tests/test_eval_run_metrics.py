from decimal import Decimal

import pytest

from app.models import EvalResult
from app.services.metrics import calculate_run_metrics


def make_result(*, score: float, passed: bool) -> EvalResult:
    return EvalResult(
        score=score,
        passed=passed,
        latency_ms=None,
        estimated_cost_usd=Decimal("0"),
        error=None,
    )


def test_mixed_results_calculate_score_and_pass_metrics() -> None:
    metrics = calculate_run_metrics(
        [
            make_result(score=1.0, passed=True),
            make_result(score=0.5, passed=False),
            make_result(score=0.0, passed=False),
        ]
    )

    assert metrics.total_count == 3
    assert metrics.completed_cases == 3
    assert metrics.failed_count == 2
    assert metrics.pass_rate == pytest.approx(1 / 3)
    assert metrics.avg_score == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("passed", "expected_pass_rate", "expected_failed_count"),
    [(True, 1.0, 0), (False, 0.0, 2)],
)
def test_all_pass_or_all_fail_metrics(
    passed: bool,
    expected_pass_rate: float,
    expected_failed_count: int,
) -> None:
    metrics = calculate_run_metrics(
        [make_result(score=float(passed), passed=passed) for _ in range(2)]
    )

    assert metrics.total_count == 2
    assert metrics.failed_count == expected_failed_count
    assert metrics.pass_rate == expected_pass_rate
    assert metrics.avg_score == float(passed)


def test_empty_results_have_null_score_metrics_and_zero_counts() -> None:
    metrics = calculate_run_metrics([])

    assert metrics.total_count == 0
    assert metrics.failed_count == 0
    assert metrics.pass_rate is None
    assert metrics.avg_score is None
