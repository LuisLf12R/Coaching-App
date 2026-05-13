"""Add Garmin training readiness metrics.

Revision ID: 20260513_0002
Revises: 20260513_0001
Create Date: 2026-05-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260513_0002"
down_revision: Union[str, None] = "20260513_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "training_readiness_metrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("data_import_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=False),
        sa.Column("calendar_date", sa.Date(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timestamp_local", sa.DateTime(timezone=True), nullable=True),
        sa.Column("level", sa.String(length=100), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("feedback_short", sa.String(length=255), nullable=True),
        sa.Column("feedback_long", sa.String(length=255), nullable=True),
        sa.Column("sleep_score", sa.Integer(), nullable=True),
        sa.Column("sleep_score_factor_percent", sa.Integer(), nullable=True),
        sa.Column("recovery_time", sa.Integer(), nullable=True),
        sa.Column("recovery_time_factor_percent", sa.Integer(), nullable=True),
        sa.Column("acwr_factor_percent", sa.Integer(), nullable=True),
        sa.Column("stress_history_factor_percent", sa.Integer(), nullable=True),
        sa.Column("hrv_factor_percent", sa.Integer(), nullable=True),
        sa.Column("sleep_history_factor_percent", sa.Integer(), nullable=True),
        sa.Column("valid_sleep", sa.Boolean(), nullable=True),
        sa.Column("input_context", sa.String(length=255), nullable=True),
        sa.Column("hrv_weekly_average", sa.Float(), nullable=True),
        sa.Column("acute_load", sa.Float(), nullable=True),
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_training_readiness_metrics_client_id_clients"),
        ),
        sa.ForeignKeyConstraint(
            ["data_import_id"],
            ["data_imports.id"],
            name=op.f("fk_training_readiness_metrics_data_import_id_data_imports"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_training_readiness_metrics")),
        sa.UniqueConstraint(
            "provider",
            "client_id",
            "calendar_date",
            name="uq_training_readiness_metrics_provider_client_date",
        ),
    )
    op.create_index(
        op.f("ix_training_readiness_metrics_calendar_date"),
        "training_readiness_metrics",
        ["calendar_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_readiness_metrics_client_id"),
        "training_readiness_metrics",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_readiness_metrics_data_import_id"),
        "training_readiness_metrics",
        ["data_import_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_readiness_metrics_provider"),
        "training_readiness_metrics",
        ["provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_training_readiness_metrics_source_record_id"),
        "training_readiness_metrics",
        ["source_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_training_readiness_metrics_source_record_id"), table_name="training_readiness_metrics")
    op.drop_index(op.f("ix_training_readiness_metrics_provider"), table_name="training_readiness_metrics")
    op.drop_index(op.f("ix_training_readiness_metrics_data_import_id"), table_name="training_readiness_metrics")
    op.drop_index(op.f("ix_training_readiness_metrics_client_id"), table_name="training_readiness_metrics")
    op.drop_index(op.f("ix_training_readiness_metrics_calendar_date"), table_name="training_readiness_metrics")
    op.drop_table("training_readiness_metrics")
