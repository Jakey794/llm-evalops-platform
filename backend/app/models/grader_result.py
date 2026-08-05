from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import JSON_DOCUMENT, Base

if TYPE_CHECKING:
    from app.models.eval_result import EvalResult


class GraderResult(Base):
    __tablename__ = "grader_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    eval_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("eval_results.id", ondelete="CASCADE"), nullable=False, index=True
    )
    grader_name: Mapped[str] = mapped_column(String(255), nullable=False)
    grader_type: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_modes: Mapped[list[str]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=list, server_default="[]"
    )
    rubric_scores: Mapped[dict[str, float]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict, server_default="{}"
    )
    raw_output: Mapped[Any | None] = mapped_column(JSON_DOCUMENT, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    eval_result: Mapped[EvalResult] = relationship(back_populates="grader_results")
