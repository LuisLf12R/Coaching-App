"""Add Garmin sleep metrics.

Revision ID: 20260513_0003
Revises: 20260513_0002
Create Date: 2026-05-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260513_0003"
down_revision: Union[str, None] = "20260513_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sleep_metrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("data_import_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=False),
        sa.Column("calendar_date", sa.Date(), nullable=False),
        sa.Column("sleep_start_gmt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sleep_end_gmt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deep_sleep_seconds", sa.Integer(), nullable=True),
        sa.Column("light_sleep_seconds", sa.Integer(), nullable=True),
        sa.Column("rem_sleep_seconds", sa.Integer(), nullable=True),
        sa.Column("awake_sleep_seconds", sa.Integer(), nullable=True),
        sa.Column("unmeasurable_seconds", sa.Integer(), nullable=True),
        sa.Column("awake_count", sa.Integer(), nullable=True),
        sa.Column("restless_moment_count", sa.Integer(), nullable=True),
        sa.Column("avg_sleep_stress", sa.Float(), nullable=True),
        sa.Column("average_respiration", sa.Float(), nullable=True),
        sa.Column("lowest_respiration", sa.Float(), nullable=True),
        sa.Column("highest_respiration", sa.Float(), nullable=True),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("duration_score", sa.Integer(), nullable=True),
        sa.Column("recovery_score", sa.Integer(), nullable=True),
        sa.Column("restfulness_score", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.String(length=255), nullable=True),
        sa.Column("insight", sa.String(length=255), nullable=True),
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_sleep_metrics_client_id_clients")),
        sa.ForeignKeyConstraint(
            ["data_import_id"],
            ["data_imports.id"],
            name=op.f("fk_sleep_metrics_data_import_id_data_imports"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sleep_metrics")),
        sa.UniqueConstraint("provider", "client_id", "calendar_date", name="uq_sleep_metrics_provider_client_date"),
    )
    op.create_index(op.f("ix_sleep_metrics_calendar_date"), "sleep_metrics", ["calendar_date"], unique=False)
    op.create_index(op.f("ix_sleep_metrics_client_id"), "sleep_metrics", ["client_id"], unique=False)
    op.create_index(op.f("ix_sleep_metrics_data_import_id"), "sleep_metrics", ["data_import_id"], unique=False)
    op.create_index(op.f("ix_sleep_metrics_provider"), "sleep_metrics", ["provider"], unique=False)
    op.create_index(op.f("ix_sleep_metrics_source_record_id"), "sleep_metrics", ["source_record_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sleep_metrics_source_record_id"), table_name="sleep_metrics")
    op.drop_index(op.f("ix_sleep_metrics_provider"), table_name="sleep_metrics")
    op.drop_index(op.f("ix_sleep_metrics_data_import_id"), table_name="sleep_metrics")
    op.drop_index(op.f("ix_sleep_metrics_client_id"), table_name="sleep_metrics")
    op.drop_index(op.f("ix_sleep_metrics_calendar_date"), table_name="sleep_metrics")
    op.drop_table("sleep_metrics")
