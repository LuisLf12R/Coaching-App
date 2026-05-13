"""Add Garmin daily wellness metrics.

Revision ID: 20260513_0006
Revises: 20260513_0005
Create Date: 2026-05-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260513_0006"
down_revision: Union[str, None] = "20260513_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_wellness_metrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("data_import_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=False),
        sa.Column("calendar_date", sa.Date(), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=True),
        sa.Column("daily_step_goal", sa.Integer(), nullable=True),
        sa.Column("wellness_distance_meters", sa.Float(), nullable=True),
        sa.Column("resting_heart_rate", sa.Integer(), nullable=True),
        sa.Column("current_day_resting_heart_rate", sa.Integer(), nullable=True),
        sa.Column("min_heart_rate", sa.Integer(), nullable=True),
        sa.Column("max_heart_rate", sa.Integer(), nullable=True),
        sa.Column("moderate_intensity_minutes", sa.Integer(), nullable=True),
        sa.Column("vigorous_intensity_minutes", sa.Integer(), nullable=True),
        sa.Column("average_stress_level", sa.Integer(), nullable=True),
        sa.Column("max_stress_level", sa.Integer(), nullable=True),
        sa.Column("stress_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("rest_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("body_battery_charged", sa.Integer(), nullable=True),
        sa.Column("body_battery_drained", sa.Integer(), nullable=True),
        sa.Column("body_battery_highest", sa.Integer(), nullable=True),
        sa.Column("body_battery_lowest", sa.Integer(), nullable=True),
        sa.Column("body_battery_most_recent", sa.Integer(), nullable=True),
        sa.Column("body_battery_start_of_day", sa.Integer(), nullable=True),
        sa.Column("body_battery_end_of_day", sa.Integer(), nullable=True),
        sa.Column("average_waking_respiration", sa.Float(), nullable=True),
        sa.Column("average_spo2", sa.Float(), nullable=True),
        sa.Column("lowest_spo2", sa.Integer(), nullable=True),
        sa.Column("latest_spo2", sa.Integer(), nullable=True),
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_daily_wellness_metrics_client_id_clients")),
        sa.ForeignKeyConstraint(
            ["data_import_id"],
            ["data_imports.id"],
            name=op.f("fk_daily_wellness_metrics_data_import_id_data_imports"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_daily_wellness_metrics")),
        sa.UniqueConstraint(
            "provider",
            "client_id",
            "calendar_date",
            name="uq_daily_wellness_metrics_provider_client_date",
        ),
    )
    op.create_index(op.f("ix_daily_wellness_metrics_calendar_date"), "daily_wellness_metrics", ["calendar_date"])
    op.create_index(op.f("ix_daily_wellness_metrics_client_id"), "daily_wellness_metrics", ["client_id"])
    op.create_index(op.f("ix_daily_wellness_metrics_data_import_id"), "daily_wellness_metrics", ["data_import_id"])
    op.create_index(op.f("ix_daily_wellness_metrics_provider"), "daily_wellness_metrics", ["provider"])
    op.create_index(op.f("ix_daily_wellness_metrics_source_record_id"), "daily_wellness_metrics", ["source_record_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_daily_wellness_metrics_source_record_id"), table_name="daily_wellness_metrics")
    op.drop_index(op.f("ix_daily_wellness_metrics_provider"), table_name="daily_wellness_metrics")
    op.drop_index(op.f("ix_daily_wellness_metrics_data_import_id"), table_name="daily_wellness_metrics")
    op.drop_index(op.f("ix_daily_wellness_metrics_client_id"), table_name="daily_wellness_metrics")
    op.drop_index(op.f("ix_daily_wellness_metrics_calendar_date"), table_name="daily_wellness_metrics")
    op.drop_table("daily_wellness_metrics")
