import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import EvalResult, EvalRun
from app.schemas.eval_results import EvalResultListItem, EvalResultResponse
from app.schemas.eval_runs import EvalRunCreate, EvalRunListItem, EvalRunResponse
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
                return failed_run
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
            select(EvalRun).order_by(EvalRun.created_at.desc(), EvalRun.id.desc()).limit(limit)
        )
    )


@router.get("/{run_id}", response_model=EvalRunResponse)
def get_eval_run(run_id: uuid.UUID, db: DbSession) -> EvalRun:
    return _get_run_or_404(db, run_id)


@router.get("/{run_id}/results", response_model=list[EvalResultResponse])
def list_eval_run_results(run_id: uuid.UUID, db: DbSession) -> list[EvalResult]:
    _get_run_or_404(db, run_id)
    return list(
        db.scalars(
            select(EvalResult)
            .where(EvalResult.eval_run_id == run_id)
            .order_by(EvalResult.created_at, EvalResult.id)
        )
    )


@router.get("/{run_id}/failed-examples", response_model=list[EvalResultListItem])
def list_failed_examples(run_id: uuid.UUID, db: DbSession) -> list[EvalResult]:
    _get_run_or_404(db, run_id)
    return list(
        db.scalars(
            select(EvalResult)
            .where(
                EvalResult.eval_run_id == run_id,
                EvalResult.error.is_not(None),
            )
            .order_by(EvalResult.created_at, EvalResult.id)
        )
    )


def _get_run_or_404(db: Session, run_id: uuid.UUID) -> EvalRun:
    eval_run = db.get(EvalRun, run_id)
    if eval_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eval run not found")
    return eval_run
