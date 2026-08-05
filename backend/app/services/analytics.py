from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from decimal import Decimal
from math import ceil
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import EvalResult, EvalRun
from app.schemas.analytics import (
    BreakdownBucket,
    CompareRunPoint,
    CompareRunsResponse,
    DashboardOverviewResponse,
    RunAnalyticsResponse,
)


def build_run_analytics(session: Session, eval_run_id: UUID) -> RunAnalyticsResponse:
    results = list(
        session.scalars(
            select(EvalResult)
            .options(selectinload(EvalResult.test_case))
            .where(EvalResult.eval_run_id == eval_run_id)
            .order_by(EvalResult.created_at, EvalResult.id)
        )
    )
    by_tag: dict[str, list[EvalResult]] = defaultdict(list)
    by_difficulty: dict[str, list[EvalResult]] = defaultdict(list)
    by_workflow: dict[str, list[EvalResult]] = defaultdict(list)
    incomplete_cases = 0

    for result in results:
        test_case = result.test_case
        if test_case is None:
            incomplete_cases += 1
            continue
        for tag in test_case.tags or ["untagged"]:
            by_tag[str(tag)].append(result)
        by_difficulty[str(test_case.difficulty or "unknown")].append(result)
        by_workflow[str(test_case.workflow_type or "unknown")].append(result)
        if result.score is None or result.passed is None:
            incomplete_cases += 1

    return RunAnalyticsResponse(
        eval_run_id=eval_run_id,
        by_tag=_buckets(by_tag),
        by_difficulty=_buckets(by_difficulty),
        by_workflow=_buckets(by_workflow),
        incomplete_cases=incomplete_cases,
        has_partial_metrics=incomplete_cases > 0
        or any(result.latency_ms is None for result in results),
    )


def build_compare_response(session: Session, run_ids: Sequence[UUID]) -> CompareRunsResponse:
    runs = _load_runs(session, run_ids)
    points = [_to_compare_point(run) for run in runs]
    return CompareRunsResponse(
        runs=points,
        cost_quality=[
            {
                "id": str(point.id),
                "label": point.label,
                "cost": point.total_cost_usd,
                "quality": point.avg_score,
            }
            for point in points
        ],
        latency_quality=[
            {
                "id": str(point.id),
                "label": point.label,
                "latency": point.p95_latency_ms
                if point.p95_latency_ms is not None
                else point.avg_latency_ms,
                "quality": point.avg_score,
            }
            for point in points
        ],
    )


def build_dashboard_overview(session: Session, *, limit: int = 20) -> DashboardOverviewResponse:
    runs = list(
        session.scalars(
            select(EvalRun)
            .options(
                selectinload(EvalRun.dataset),
                selectinload(EvalRun.prompt_version),
                selectinload(EvalRun.model_config),
            )
            .order_by(EvalRun.created_at.desc(), EvalRun.id.desc())
            .limit(limit)
        )
    )
    points = [_to_compare_point(run) for run in runs]
    completed = [run for run in runs if run.status == "completed"]
    pass_rates = [run.pass_rate for run in completed if run.pass_rate is not None]
    scores = [run.avg_score for run in completed if run.avg_score is not None]
    latencies = [run.avg_latency_ms for run in completed if run.avg_latency_ms is not None]
    p95s = sorted(run.p95_latency_ms for run in completed if run.p95_latency_ms is not None)
    total_cost = sum((run.total_cost_usd for run in completed), start=Decimal("0"))
    has_partial = any(
        run.pass_rate is None or run.avg_score is None or run.avg_latency_ms is None
        for run in completed
    )

    return DashboardOverviewResponse(
        run_count=len(runs),
        completed_run_count=len(completed),
        pass_rate=(sum(pass_rates) / len(pass_rates)) if pass_rates else None,
        avg_score=(sum(scores) / len(scores)) if scores else None,
        total_cost_usd=float(total_cost),
        avg_latency_ms=(sum(latencies) / len(latencies)) if latencies else None,
        p95_latency_ms=p95s[ceil(0.95 * len(p95s)) - 1] if p95s else None,
        has_partial_metrics=has_partial,
        recent_runs=points,
    )


def _load_runs(session: Session, run_ids: Sequence[UUID]) -> list[EvalRun]:
    if not run_ids:
        return []
    runs = list(
        session.scalars(
            select(EvalRun)
            .options(
                selectinload(EvalRun.dataset),
                selectinload(EvalRun.prompt_version),
                selectinload(EvalRun.model_config),
            )
            .where(EvalRun.id.in_(run_ids))
        )
    )
    by_id = {run.id: run for run in runs}
    return [by_id[run_id] for run_id in run_ids if run_id in by_id]


def _to_compare_point(run: EvalRun) -> CompareRunPoint:
    prompt = run.prompt_version
    model = run.model_config
    dataset = run.dataset
    label_parts = [
        dataset.name if dataset is not None else None,
        prompt.name if prompt is not None else None,
        model.model_name if model is not None else None,
    ]
    label = " / ".join(part for part in label_parts if part) or str(run.id)
    return CompareRunPoint(
        id=run.id,
        label=label,
        status=run.status,
        dataset_name=dataset.name if dataset is not None else None,
        prompt_name=prompt.name if prompt is not None else None,
        prompt_version_label=prompt.version_label if prompt is not None else None,
        model_name=model.model_name if model is not None else None,
        pass_rate=run.pass_rate,
        avg_score=run.avg_score,
        total_cost_usd=float(run.total_cost_usd or 0),
        avg_latency_ms=run.avg_latency_ms,
        p95_latency_ms=run.p95_latency_ms,
        failed_count=run.failed_count,
        total_count=run.total_cases,
    )


def _buckets(grouped: dict[str, list[EvalResult]]) -> list[BreakdownBucket]:
    buckets: list[BreakdownBucket] = []
    for key in sorted(grouped):
        buckets.append(_bucket_from_results(key, grouped[key]))
    return buckets


def _bucket_from_results(key: str, results: Iterable[EvalResult]) -> BreakdownBucket:
    result_list = list(results)
    scores = [float(result.score) for result in result_list if result.score is not None]
    latencies = [
        float(result.latency_ms) for result in result_list if result.latency_ms is not None
    ]
    passed_count = sum(result.passed is True for result in result_list)
    failed_count = sum(result.passed is False for result in result_list)
    total_count = len(result_list)
    total_cost = sum(
        (
            result.estimated_cost_usd
            for result in result_list
            if result.estimated_cost_usd is not None
        ),
        start=Decimal("0"),
    )
    return BreakdownBucket(
        key=key,
        total_count=total_count,
        passed_count=passed_count,
        failed_count=failed_count,
        pass_rate=(passed_count / total_count) if total_count else None,
        avg_score=(sum(scores) / len(scores)) if scores else None,
        avg_latency_ms=(sum(latencies) / len(latencies)) if latencies else None,
        total_cost_usd=float(total_cost),
    )
