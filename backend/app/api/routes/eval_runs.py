import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import EvalResult, EvalRun, GraderResult
from app.schemas.analytics import (
    CompareRunsResponse,
    DashboardOverviewResponse,
    RunAnalyticsResponse,
)
from app.schemas.eval_results import (
    EvalResultResponse,
    FailedExampleResponse,
    GraderErrorResponse,
    GraderResultResponse,
)
from app.schemas.eval_runs import EvalRunCreate, EvalRunListItem, EvalRunResponse
from app.security import OperatorPrincipal
from app.services.analytics import (
    build_compare_response,
    build_dashboard_overview,
    build_run_analytics,
)
from app.services.eval_runner import (
    EvalResourceNotFoundError,
    EvalRunner,
    EvalRunSetupError,
    ProviderFactory,
    default_provider_factory,
)

router = APIRouter(prefix="/eval-runs", tags=["eval-runs"])
DbSession = Annotated[Session, Depends(get_db)]


def get_provider_factory() -> ProviderFactory:
    """Provide the runtime LLM provider factory and an API-test override seam."""
    return default_provider_factory


ProviderFactoryDependency = Annotated[ProviderFactory, Depends(get_provider_factory)]


@router.post("", response_model=EvalRunResponse, status_code=status.HTTP_201_CREATED)
def create_eval_run(
    request: EvalRunCreate,
    db: DbSession,
    provider_factory: ProviderFactoryDependency,
    _principal: OperatorPrincipal,
) -> EvalRun:
    runner = EvalRunner(db, provider_factory=provider_factory)
    try:
        return runner.run(
            dataset_id=request.dataset_id,
            prompt_version_id=request.prompt_version_id,
            model_config_id=request.model_config_id,
        )
    except EvalResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except EvalRunSetupError as exc:
        if exc.run_id is not None:
            failed_run = db.get(EvalRun, exc.run_id)
            if failed_run is not None:
                return _load_run(db, failed_run.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Eval run setup failed",
        ) from exc


@router.get("", response_model=list[EvalRunListItem])
def list_eval_runs(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[EvalRun]:
    return list(
        db.scalars(
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


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DashboardOverviewResponse:
    return build_dashboard_overview(db, limit=limit)


@router.get("/compare", response_model=CompareRunsResponse)
def compare_eval_runs(
    db: DbSession,
    run_ids: Annotated[list[uuid.UUID], Query(min_length=1, max_length=10)],
) -> CompareRunsResponse:
    response = build_compare_response(db, run_ids)
    if len(response.runs) != len(set(run_ids)):
        missing = sorted(
            {str(run_id) for run_id in run_ids} - {str(run.id) for run in response.runs}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Eval run not found: {', '.join(missing)}",
        )
    return response


@router.get("/{run_id}", response_model=EvalRunResponse)
def get_eval_run(run_id: uuid.UUID, db: DbSession) -> EvalRun:
    return _get_run_or_404(db, run_id)


@router.get("/{run_id}/analytics", response_model=RunAnalyticsResponse)
def get_eval_run_analytics(run_id: uuid.UUID, db: DbSession) -> RunAnalyticsResponse:
    _get_run_or_404(db, run_id)
    return build_run_analytics(db, run_id)


@router.get("/{run_id}/results", response_model=list[EvalResultResponse])
def list_eval_run_results(run_id: uuid.UUID, db: DbSession) -> list[EvalResult]:
    _get_run_or_404(db, run_id)
    return list(
        db.scalars(
            select(EvalResult)
            .options(selectinload(EvalResult.grader_results))
            .where(EvalResult.eval_run_id == run_id)
            .order_by(EvalResult.created_at, EvalResult.id)
        )
    )


@router.get("/{run_id}/failed-examples", response_model=list[FailedExampleResponse])
def list_failed_examples(run_id: uuid.UUID, db: DbSession) -> list[FailedExampleResponse]:
    _get_run_or_404(db, run_id)
    results = list(
        db.scalars(
            select(EvalResult)
            .options(
                selectinload(EvalResult.test_case),
                selectinload(EvalResult.grader_results),
            )
            .where(
                EvalResult.eval_run_id == run_id,
                or_(
                    EvalResult.passed.is_(False),
                    EvalResult.error.is_not(None),
                    EvalResult.grader_results.any(GraderResult.error.is_not(None)),
                ),
            )
            .order_by(EvalResult.created_at, EvalResult.id)
        )
    )
    return [_to_failed_example(result) for result in results]


def _get_run_or_404(db: Session, run_id: uuid.UUID) -> EvalRun:
    return _load_run(db, run_id)


def _load_run(db: Session, run_id: uuid.UUID) -> EvalRun:
    eval_run = db.scalars(
        select(EvalRun)
        .options(
            selectinload(EvalRun.dataset),
            selectinload(EvalRun.prompt_version),
            selectinload(EvalRun.model_config),
        )
        .where(EvalRun.id == run_id)
    ).first()
    if eval_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eval run not found")
    return eval_run


def _to_failed_example(result: EvalResult) -> FailedExampleResponse:
    test_case = result.test_case
    grader_results = list(result.grader_results)
    deterministic_scores = {
        grader.grader_name: grader.score
        for grader in grader_results
        if grader.grader_type == "deterministic" and grader.score is not None
    }
    judge_result = next(
        (grader for grader in grader_results if grader.grader_name == "llm_judge"),
        None,
    )
    grader_errors = [
        GraderErrorResponse(grader_name=grader.grader_name, error=grader.error)
        for grader in grader_results
        if grader.error is not None
    ]
    if result.error is not None:
        grader_errors.insert(
            0,
            GraderErrorResponse(grader_name="model_provider", error=result.error),
        )

    return FailedExampleResponse(
        id=result.id,
        eval_run_id=result.eval_run_id,
        test_case_id=result.test_case_id,
        workflow_type=test_case.workflow_type,
        difficulty=test_case.difficulty,
        tags=test_case.tags,
        input_json=test_case.input_json,
        expected_output_json=test_case.expected_output_json,
        model_output=result.model_output,
        final_score=result.score,
        passed=result.passed,
        deterministic_grader_scores=deterministic_scores,
        llm_judge_score=judge_result.score if judge_result is not None else None,
        judge_reason=judge_result.feedback if judge_result is not None else None,
        failure_modes=result.failure_modes,
        rubric_scores=judge_result.rubric_scores if judge_result is not None else {},
        grader_errors=grader_errors,
        grader_results=[GraderResultResponse.model_validate(grader) for grader in grader_results],
        created_at=result.created_at,
    )
