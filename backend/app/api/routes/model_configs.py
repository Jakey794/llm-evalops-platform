"""List model configurations for the dashboard run launcher."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ModelConfig
from app.schemas.model_configs import ModelConfigListItem, ModelConfigResponse

router = APIRouter(prefix="/model-configs", tags=["model-configs"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ModelConfigListItem])
def list_model_configs(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[ModelConfig]:
    return list(
        db.scalars(
            select(ModelConfig)
            .order_by(ModelConfig.provider, ModelConfig.model_name, ModelConfig.created_at.desc())
            .limit(limit)
        )
    )


@router.get("/{model_config_id}", response_model=ModelConfigResponse)
def get_model_config(model_config_id: UUID, db: DbSession) -> ModelConfig:
    model = db.get(ModelConfig, model_config_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model config not found",
        )
    return model
