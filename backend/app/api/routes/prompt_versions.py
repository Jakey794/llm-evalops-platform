"""List prompt versions for the dashboard."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PromptVersion
from app.schemas.prompt_versions import PromptVersionListItem, PromptVersionResponse

router = APIRouter(prefix="/prompt-versions", tags=["prompt-versions"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[PromptVersionListItem])
def list_prompt_versions(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[PromptVersion]:
    return list(
        db.scalars(
            select(PromptVersion)
            .order_by(PromptVersion.workflow_type, PromptVersion.name, PromptVersion.version_label)
            .limit(limit)
        )
    )


@router.get("/{prompt_version_id}", response_model=PromptVersionResponse)
def get_prompt_version(prompt_version_id: str, db: DbSession) -> PromptVersion:
    from uuid import UUID

    from fastapi import HTTPException, status

    prompt = db.get(PromptVersion, UUID(prompt_version_id))
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prompt version not found"
        )
    return prompt
