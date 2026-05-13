from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
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
    training_readiness_metrics: Mapped[list["TrainingReadinessMetric"]] = relationship(back_populates="client")
    sleep_metrics: Mapped[list["SleepMetric"]] = relationship(back_populates="client")
    health_status_metrics: Mapped[list["HealthStatusMetric"]] = relationship(back_populates="client")
    acute_training_load_metrics: Mapped[list["AcuteTrainingLoadMetric"]] = relationship(back_populates="client")
    daily_wellness_metrics: Mapped[list["DailyWellnessMetric"]] = relationship(back_populates="client")


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
    training_readiness_metrics: Mapped[list["TrainingReadinessMetric"]] = relationship(back_populates="data_import")
    sleep_metrics: Mapped[list["SleepMetric"]] = relationship(back_populates="data_import")
    health_status_metrics: Mapped[list["HealthStatusMetric"]] = relationship(back_populates="data_import")
    acute_training_load_metrics: Mapped[list["AcuteTrainingLoadMetric"]] = relationship(back_populates="data_import")
    daily_wellness_metrics: Mapped[list["DailyWellnessMetric"]] = relationship(back_populates="data_import")


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


class TrainingReadinessMetric(Base):
    __tablename__ = "training_readiness_metrics"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "client_id",
            "calendar_date",
            name="uq_training_readiness_metrics_provider_client_date",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    data_import_id: Mapped[str] = mapped_column(ForeignKey("data_imports.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    calendar_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    timestamp_local: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    level: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback_short: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    feedback_long: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sleep_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sleep_score_factor_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recovery_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recovery_time_factor_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    acwr_factor_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stress_history_factor_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hrv_factor_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sleep_history_factor_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    valid_sleep: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    input_context: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hrv_weekly_average: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    acute_load: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    provider_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(json_storage_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    client: Mapped["Client"] = relationship(back_populates="training_readiness_metrics")
    data_import: Mapped["DataImport"] = relationship(back_populates="training_readiness_metrics")


class SleepMetric(Base):
    __tablename__ = "sleep_metrics"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "client_id",
            "calendar_date",
            name="uq_sleep_metrics_provider_client_date",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    data_import_id: Mapped[str] = mapped_column(ForeignKey("data_imports.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    calendar_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    sleep_start_gmt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sleep_end_gmt: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deep_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    light_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rem_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    awake_sleep_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    unmeasurable_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    awake_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    restless_moment_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_sleep_stress: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    average_respiration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lowest_respiration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    highest_respiration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    overall_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quality_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recovery_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    restfulness_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    insight: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(json_storage_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    client: Mapped["Client"] = relationship(back_populates="sleep_metrics")
    data_import: Mapped["DataImport"] = relationship(back_populates="sleep_metrics")


class HealthStatusMetric(Base):
    __tablename__ = "health_status_metrics"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "client_id",
            "calendar_date",
            name="uq_health_status_metrics_provider_client_date",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    data_import_id: Mapped[str] = mapped_column(ForeignKey("data_imports.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    calendar_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    create_timestamp_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    update_timestamp_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    outliers_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    heart_rate_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    heart_rate_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    heart_rate_baseline_lower: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    heart_rate_baseline_upper: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hrv_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hrv_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hrv_baseline_lower: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hrv_baseline_upper: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    respiration_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    respiration_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    spo2_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spo2_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    skin_temp_c_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    skin_temp_c_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(json_storage_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    client: Mapped["Client"] = relationship(back_populates="health_status_metrics")
    data_import: Mapped["DataImport"] = relationship(back_populates="health_status_metrics")


class AcuteTrainingLoadMetric(Base):
    __tablename__ = "acute_training_load_metrics"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "client_id",
            "calendar_date",
            name="uq_acute_training_load_metrics_provider_client_date",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    data_import_id: Mapped[str] = mapped_column(ForeignKey("data_imports.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    calendar_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acwr_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    acwr_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    acwr_status_feedback: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    daily_training_load_acute: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    daily_training_load_chronic: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    daily_acute_chronic_workload_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    provider_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(json_storage_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    client: Mapped["Client"] = relationship(back_populates="acute_training_load_metrics")
    data_import: Mapped["DataImport"] = relationship(back_populates="acute_training_load_metrics")


class DailyWellnessMetric(Base):
    __tablename__ = "daily_wellness_metrics"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "client_id",
            "calendar_date",
            name="uq_daily_wellness_metrics_provider_client_date",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    data_import_id: Mapped[str] = mapped_column(ForeignKey("data_imports.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    calendar_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    total_steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    daily_step_goal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wellness_distance_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resting_heart_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_day_resting_heart_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_heart_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_heart_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    moderate_intensity_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vigorous_intensity_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    average_stress_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_stress_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stress_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rest_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    body_battery_charged: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    body_battery_drained: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    body_battery_highest: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    body_battery_lowest: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    body_battery_most_recent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    body_battery_start_of_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    body_battery_end_of_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    average_waking_respiration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    average_spo2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lowest_spo2: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latest_spo2: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    provider_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(json_storage_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    client: Mapped["Client"] = relationship(back_populates="daily_wellness_metrics")
    data_import: Mapped["DataImport"] = relationship(back_populates="daily_wellness_metrics")
