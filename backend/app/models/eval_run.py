from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import EvalRunStatus

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.eval_result import EvalResult
    from app.models.model_config import ModelConfig
    from app.models.prompt_version import PromptVersion


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prompt_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    model_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("model_configs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=EvalRunStatus.PENDING.value,
        server_default=EvalRunStatus.PENDING.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completed_cases: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    pass_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 8), nullable=False, default=Decimal("0"), server_default="0"
    )
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p95_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    dataset: Mapped[Dataset] = relationship(back_populates="eval_runs")
    prompt_version: Mapped[PromptVersion] = relationship(back_populates="eval_runs")
    model_config: Mapped[ModelConfig] = relationship(back_populates="eval_runs")
    results: Mapped[list[EvalResult]] = relationship(
        back_populates="eval_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def total_count(self) -> int:
        return self.total_cases

    @property
    def model_name(self) -> str | None:
        return self.model_config.model_name if self.model_config is not None else None

    @property
    def dataset_name(self) -> str | None:
        return self.dataset.name if self.dataset is not None else None

    @property
    def prompt_name(self) -> str | None:
        return self.prompt_version.name if self.prompt_version is not None else None

    @property
    def prompt_version_label(self) -> str | None:
        return self.prompt_version.version_label if self.prompt_version is not None else None
