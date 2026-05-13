"""Create initial coaching data schema.

Revision ID: 20260513_0001
Revises:
Create Date: 2026-05-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260513_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coaches",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("auth_provider", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_coaches")),
        sa.UniqueConstraint("email", name=op.f("uq_coaches_email")),
    )
    op.create_index(op.f("ix_coaches_email"), "coaches", ["email"], unique=False)

    op.create_table(
        "activity_type_mappings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("provider_activity_type", sa.String(length=255), nullable=False),
        sa.Column("provider_sport_type", sa.String(length=255), nullable=True),
        sa.Column("normalized_activity_type", sa.String(length=100), nullable=False),
        sa.Column("normalized_sport", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_type_mappings")),
        sa.UniqueConstraint(
            "provider",
            "provider_activity_type",
            "provider_sport_type",
            name="uq_activity_type_mappings_provider_types",
        ),
    )
    op.create_index(
        op.f("ix_activity_type_mappings_provider"),
        "activity_type_mappings",
        ["provider"],
        unique=False,
    )

    op.create_table(
        "clients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("coach_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("sport_focus", sa.String(length=100), nullable=True),
        sa.Column("goals", sa.Text(), nullable=True),
        sa.Column("injury_notes", sa.Text(), nullable=True),
        sa.Column("training_constraints", sa.Text(), nullable=True),
        sa.Column("coach_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["coach_id"], ["coaches.id"], name=op.f("fk_clients_coach_id_coaches")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clients")),
    )
    op.create_index(op.f("ix_clients_coach_id"), "clients", ["coach_id"], unique=False)

    op.create_table(
        "data_imports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("source_name", sa.String(length=500), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_data_imports_client_id_clients")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_imports")),
    )
    op.create_index(op.f("ix_data_imports_client_id"), "data_imports", ["client_id"], unique=False)
    op.create_index(op.f("ix_data_imports_provider"), "data_imports", ["provider"], unique=False)

    op.create_table(
        "activities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("data_import_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("source_activity_id", sa.String(length=255), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        sa.Column("activity_type", sa.String(length=100), nullable=False),
        sa.Column("sport_type", sa.String(length=100), nullable=True),
        sa.Column("start_time_gmt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_time_local", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("distance_meters", sa.Float(), nullable=True),
        sa.Column("avg_speed_meters_per_second", sa.Float(), nullable=True),
        sa.Column("avg_hr", sa.Integer(), nullable=True),
        sa.Column("max_hr", sa.Integer(), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("training_effect_label", sa.String(length=100), nullable=True),
        sa.Column("activity_training_load", sa.Float(), nullable=True),
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_activities_client_id_clients")),
        sa.ForeignKeyConstraint(
            ["data_import_id"],
            ["data_imports.id"],
            name=op.f("fk_activities_data_import_id_data_imports"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activities")),
        sa.UniqueConstraint("provider", "source_activity_id", name="uq_activities_provider_source_activity_id"),
    )
    op.create_index(op.f("ix_activities_activity_type"), "activities", ["activity_type"], unique=False)
    op.create_index(op.f("ix_activities_client_id"), "activities", ["client_id"], unique=False)
    op.create_index(op.f("ix_activities_data_import_id"), "activities", ["data_import_id"], unique=False)
    op.create_index(op.f("ix_activities_provider"), "activities", ["provider"], unique=False)
    op.create_index(op.f("ix_activities_source_activity_id"), "activities", ["source_activity_id"], unique=False)
    op.create_index(op.f("ix_activities_sport_type"), "activities", ["sport_type"], unique=False)
    op.create_index(op.f("ix_activities_start_time_gmt"), "activities", ["start_time_gmt"], unique=False)

    op.create_table(
        "raw_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("data_import_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("source_name", sa.String(length=500), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=True),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column("validation_status", sa.String(length=50), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["data_import_id"],
            ["data_imports.id"],
            name=op.f("fk_raw_records_data_import_id_data_imports"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raw_records")),
    )
    op.create_index(op.f("ix_raw_records_data_import_id"), "raw_records", ["data_import_id"], unique=False)
    op.create_index(op.f("ix_raw_records_provider"), "raw_records", ["provider"], unique=False)
    op.create_index(op.f("ix_raw_records_source_record_id"), "raw_records", ["source_record_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_raw_records_source_record_id"), table_name="raw_records")
    op.drop_index(op.f("ix_raw_records_provider"), table_name="raw_records")
    op.drop_index(op.f("ix_raw_records_data_import_id"), table_name="raw_records")
    op.drop_table("raw_records")
    op.drop_index(op.f("ix_activities_start_time_gmt"), table_name="activities")
    op.drop_index(op.f("ix_activities_sport_type"), table_name="activities")
    op.drop_index(op.f("ix_activities_source_activity_id"), table_name="activities")
    op.drop_index(op.f("ix_activities_provider"), table_name="activities")
    op.drop_index(op.f("ix_activities_data_import_id"), table_name="activities")
    op.drop_index(op.f("ix_activities_client_id"), table_name="activities")
    op.drop_index(op.f("ix_activities_activity_type"), table_name="activities")
    op.drop_table("activities")
    op.drop_index(op.f("ix_data_imports_provider"), table_name="data_imports")
    op.drop_index(op.f("ix_data_imports_client_id"), table_name="data_imports")
    op.drop_table("data_imports")
    op.drop_index(op.f("ix_clients_coach_id"), table_name="clients")
    op.drop_table("clients")
    op.drop_index(op.f("ix_activity_type_mappings_provider"), table_name="activity_type_mappings")
    op.drop_table("activity_type_mappings")
    op.drop_index(op.f("ix_coaches_email"), table_name="coaches")
    op.drop_table("coaches")
