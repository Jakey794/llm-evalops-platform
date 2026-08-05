"""create grader results

Revision ID: c2d5e8f1a9b4
Revises: b7e4c9d2a6f1
Create Date: 2026-07-06 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d5e8f1a9b4"
down_revision: str | Sequence[str] | None = "b7e4c9d2a6f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create persistent per-grader results."""
    op.create_table(
        "grader_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("eval_result_id", sa.Uuid(), nullable=False),
        sa.Column("grader_name", sa.String(length=255), nullable=False),
        sa.Column("grader_type", sa.String(length=100), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column(
            "failure_modes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "rubric_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("raw_output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["eval_result_id"],
            ["eval_results.id"],
            name=op.f("fk_grader_results_eval_result_id_eval_results"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grader_results")),
    )
    op.create_index(
        op.f("ix_grader_results_eval_result_id"),
        "grader_results",
        ["eval_result_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop persistent per-grader results."""
    op.drop_index(op.f("ix_grader_results_eval_result_id"), table_name="grader_results")
    op.drop_table("grader_results")
