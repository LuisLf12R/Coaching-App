"""Add Garmin health-status metrics.

Revision ID: 20260513_0004
Revises: 20260513_0003
Create Date: 2026-05-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260513_0004"
down_revision: Union[str, None] = "20260513_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "health_status_metrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("data_import_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=False),
        sa.Column("calendar_date", sa.Date(), nullable=False),
        sa.Column("create_timestamp_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("update_timestamp_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outliers_count", sa.Integer(), nullable=True),
        sa.Column("heart_rate_value", sa.Float(), nullable=True),
        sa.Column("heart_rate_status", sa.String(length=100), nullable=True),
        sa.Column("heart_rate_baseline_lower", sa.Float(), nullable=True),
        sa.Column("heart_rate_baseline_upper", sa.Float(), nullable=True),
        sa.Column("hrv_value", sa.Float(), nullable=True),
        sa.Column("hrv_status", sa.String(length=100), nullable=True),
        sa.Column("hrv_baseline_lower", sa.Float(), nullable=True),
        sa.Column("hrv_baseline_upper", sa.Float(), nullable=True),
        sa.Column("respiration_value", sa.Float(), nullable=True),
        sa.Column("respiration_status", sa.String(length=100), nullable=True),
        sa.Column("spo2_value", sa.Float(), nullable=True),
        sa.Column("spo2_status", sa.String(length=100), nullable=True),
        sa.Column("skin_temp_c_value", sa.Float(), nullable=True),
        sa.Column("skin_temp_c_status", sa.String(length=100), nullable=True),
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_health_status_metrics_client_id_clients"),
        ),
        sa.ForeignKeyConstraint(
            ["data_import_id"],
            ["data_imports.id"],
            name=op.f("fk_health_status_metrics_data_import_id_data_imports"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_health_status_metrics")),
        sa.UniqueConstraint(
            "provider",
            "client_id",
            "calendar_date",
            name="uq_health_status_metrics_provider_client_date",
        ),
    )
    op.create_index(op.f("ix_health_status_metrics_calendar_date"), "health_status_metrics", ["calendar_date"], unique=False)
    op.create_index(op.f("ix_health_status_metrics_client_id"), "health_status_metrics", ["client_id"], unique=False)
    op.create_index(op.f("ix_health_status_metrics_data_import_id"), "health_status_metrics", ["data_import_id"], unique=False)
    op.create_index(op.f("ix_health_status_metrics_provider"), "health_status_metrics", ["provider"], unique=False)
    op.create_index(
        op.f("ix_health_status_metrics_source_record_id"),
        "health_status_metrics",
        ["source_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_health_status_metrics_source_record_id"), table_name="health_status_metrics")
    op.drop_index(op.f("ix_health_status_metrics_provider"), table_name="health_status_metrics")
    op.drop_index(op.f("ix_health_status_metrics_data_import_id"), table_name="health_status_metrics")
    op.drop_index(op.f("ix_health_status_metrics_client_id"), table_name="health_status_metrics")
    op.drop_index(op.f("ix_health_status_metrics_calendar_date"), table_name="health_status_metrics")
    op.drop_table("health_status_metrics")
