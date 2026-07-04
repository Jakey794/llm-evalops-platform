"""add grader outputs to eval results

Revision ID: b7e4c9d2a6f1
Revises: 8f3c2d7a4b1e
Create Date: 2026-07-04 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e4c9d2a6f1"
down_revision: str | Sequence[str] | None = "8f3c2d7a4b1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist deterministic grader outputs and failed-result counts."""
    op.add_column(
        "eval_results",
        sa.Column("score", sa.Float(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "eval_results",
        sa.Column("passed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "eval_results",
        sa.Column("grader_feedback", sa.Text(), server_default=sa.text("''"), nullable=False),
    )
    op.add_column(
        "eval_results",
        sa.Column(
            "failure_modes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "eval_results",
        sa.Column(
            "grader_breakdown",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "eval_runs",
        sa.Column("failed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    """Remove deterministic grader outputs and failed-result counts."""
    op.drop_column("eval_runs", "failed_count")
    op.drop_column("eval_results", "grader_breakdown")
    op.drop_column("eval_results", "failure_modes")
    op.drop_column("eval_results", "grader_feedback")
    op.drop_column("eval_results", "passed")
    op.drop_column("eval_results", "score")
