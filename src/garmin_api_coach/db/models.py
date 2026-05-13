from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from garmin_api_coach.db.base import Base


json_storage_type = JSONB().with_variant(JSON(), "sqlite")


def generate_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Coach(Base):
    __tablename__ = "coaches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    clients: Mapped[list["Client"]] = relationship(back_populates="coach")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    coach_id: Mapped[str] = mapped_column(ForeignKey("coaches.id"), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sport_focus: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    goals: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    injury_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    training_constraints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    coach_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    coach: Mapped["Coach"] = relationship(back_populates="clients")
    imports: Mapped[list["DataImport"]] = relationship(back_populates="client")
    activities: Mapped[list["Activity"]] = relationship(back_populates="client")


class DataImport(Base):
    __tablename__ = "data_imports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[Optional[dict[str, Any]]] = mapped_column(json_storage_type, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    client: Mapped["Client"] = relationship(back_populates="imports")
    raw_records: Mapped[list["RawRecord"]] = relationship(back_populates="data_import")
    activities: Mapped[list["Activity"]] = relationship(back_populates="data_import")


class RawRecord(Base):
    __tablename__ = "raw_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    data_import_id: Mapped[str] = mapped_column(ForeignKey("data_imports.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(500), nullable=False)
    source_record_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(json_storage_type, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    data_import: Mapped["DataImport"] = relationship(back_populates="raw_records")


class ActivityTypeMapping(Base):
    __tablename__ = "activity_type_mappings"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_activity_type",
            "provider_sport_type",
            name="uq_activity_type_mappings_provider_types",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider_activity_type: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_sport_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    normalized_activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_sport: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("provider", "source_activity_id", name="uq_activities_provider_source_activity_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    data_import_id: Mapped[str] = mapped_column(ForeignKey("data_imports.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_activity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sport_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    start_time_gmt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    start_time_local: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    distance_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_speed_meters_per_second: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    calories: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    training_effect_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    activity_training_load: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    provider_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(json_storage_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    client: Mapped["Client"] = relationship(back_populates="activities")
    data_import: Mapped["DataImport"] = relationship(back_populates="activities")
