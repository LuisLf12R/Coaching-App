"""Add Garmin acute training load metrics.

Revision ID: 20260513_0005
Revises: 20260513_0004
Create Date: 2026-05-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260513_0005"
down_revision: Union[str, None] = "20260513_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "acute_training_load_metrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("data_import_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=False),
        sa.Column("calendar_date", sa.Date(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acwr_percent", sa.Integer(), nullable=True),
        sa.Column("acwr_status", sa.String(length=100), nullable=True),
        sa.Column("acwr_status_feedback", sa.String(length=100), nullable=True),
        sa.Column("daily_training_load_acute", sa.Float(), nullable=True),
        sa.Column("daily_training_load_chronic", sa.Float(), nullable=True),
        sa.Column("daily_acute_chronic_workload_ratio", sa.Float(), nullable=True),
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_acute_training_load_metrics_client_id_clients"),
        ),
        sa.ForeignKeyConstraint(
            ["data_import_id"],
            ["data_imports.id"],
            name=op.f("fk_acute_training_load_metrics_data_import_id_data_imports"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acute_training_load_metrics")),
        sa.UniqueConstraint(
            "provider",
            "client_id",
            "calendar_date",
            name="uq_acute_training_load_metrics_provider_client_date",
        ),
    )
    op.create_index(
        op.f("ix_acute_training_load_metrics_calendar_date"),
        "acute_training_load_metrics",
        ["calendar_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_acute_training_load_metrics_client_id"),
        "acute_training_load_metrics",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_acute_training_load_metrics_data_import_id"),
        "acute_training_load_metrics",
        ["data_import_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_acute_training_load_metrics_provider"),
        "acute_training_load_metrics",
        ["provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_acute_training_load_metrics_source_record_id"),
        "acute_training_load_metrics",
        ["source_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_acute_training_load_metrics_source_record_id"), table_name="acute_training_load_metrics")
    op.drop_index(op.f("ix_acute_training_load_metrics_provider"), table_name="acute_training_load_metrics")
    op.drop_index(op.f("ix_acute_training_load_metrics_data_import_id"), table_name="acute_training_load_metrics")
    op.drop_index(op.f("ix_acute_training_load_metrics_client_id"), table_name="acute_training_load_metrics")
    op.drop_index(op.f("ix_acute_training_load_metrics_calendar_date"), table_name="acute_training_load_metrics")
    op.drop_table("acute_training_load_metrics")
