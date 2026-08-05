"""create eval runner tables

Revision ID: 8f3c2d7a4b1e
Revises: 16a3d1913db0
Create Date: 2026-06-29 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f3c2d7a4b1e"
down_revision: str | Sequence[str] | None = "16a3d1913db0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create prompt, model configuration, eval run, and eval result tables."""
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("workflow_type", sa.String(length=100), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("version_label", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_versions")),
        sa.UniqueConstraint(
            "workflow_type",
            "name",
            "version_label",
            name="uq_prompt_versions_workflow_name_version",
        ),
    )
    op.create_index(
        op.f("ix_prompt_versions_workflow_type"),
        "prompt_versions",
        ["workflow_type"],
        unique=False,
    )

    op.create_table(
        "model_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column(
            "response_format",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_configs")),
    )
    op.create_index(op.f("ix_model_configs_provider"), "model_configs", ["provider"], unique=False)

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_version_id", sa.Uuid(), nullable=False),
        sa.Column("model_config_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_cases", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completed_cases", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("pass_rate", sa.Float(), nullable=True),
        sa.Column("avg_score", sa.Float(), nullable=True),
        sa.Column(
            "total_cost_usd",
            sa.Numeric(precision=14, scale=8),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.Column("p95_latency_ms", sa.Float(), nullable=True),
        sa.Column("error_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_eval_runs_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_config_id"],
            ["model_configs.id"],
            name=op.f("fk_eval_runs_model_config_id_model_configs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prompt_version_id"],
            ["prompt_versions.id"],
            name=op.f("fk_eval_runs_prompt_version_id_prompt_versions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eval_runs")),
    )
    op.create_index(op.f("ix_eval_runs_dataset_id"), "eval_runs", ["dataset_id"], unique=False)
    op.create_index(
        op.f("ix_eval_runs_model_config_id"), "eval_runs", ["model_config_id"], unique=False
    )
    op.create_index(
        op.f("ix_eval_runs_prompt_version_id"),
        "eval_runs",
        ["prompt_version_id"],
        unique=False,
    )
    op.create_index(op.f("ix_eval_runs_status"), "eval_runs", ["status"], unique=False)

    op.create_table(
        "eval_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("eval_run_id", sa.Uuid(), nullable=False),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.Column("model_output", sa.Text(), nullable=True),
        sa.Column(
            "parsed_output",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "raw_response",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["eval_run_id"],
            ["eval_runs.id"],
            name=op.f("fk_eval_results_eval_run_id_eval_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["test_cases.id"],
            name=op.f("fk_eval_results_test_case_id_test_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eval_results")),
        sa.UniqueConstraint(
            "eval_run_id",
            "test_case_id",
            name="uq_eval_results_run_test_case",
        ),
    )
    op.create_index(
        op.f("ix_eval_results_eval_run_id"), "eval_results", ["eval_run_id"], unique=False
    )
    op.create_index(
        op.f("ix_eval_results_test_case_id"), "eval_results", ["test_case_id"], unique=False
    )


def downgrade() -> None:
    """Drop eval runner tables in reverse dependency order."""
    op.drop_index(op.f("ix_eval_results_test_case_id"), table_name="eval_results")
    op.drop_index(op.f("ix_eval_results_eval_run_id"), table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_index(op.f("ix_eval_runs_status"), table_name="eval_runs")
    op.drop_index(op.f("ix_eval_runs_prompt_version_id"), table_name="eval_runs")
    op.drop_index(op.f("ix_eval_runs_model_config_id"), table_name="eval_runs")
    op.drop_index(op.f("ix_eval_runs_dataset_id"), table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_index(op.f("ix_model_configs_provider"), table_name="model_configs")
    op.drop_table("model_configs")
    op.drop_index(op.f("ix_prompt_versions_workflow_type"), table_name="prompt_versions")
    op.drop_table("prompt_versions")
