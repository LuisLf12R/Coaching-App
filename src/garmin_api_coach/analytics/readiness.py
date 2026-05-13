from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from garmin_api_coach.analytics.activity_overview import build_activity_overview
from garmin_api_coach.db.models import Activity, Client, TrainingReadinessMetric


RECOVERY_INPUTS = (
    "sleep",
    "hrv",
    "resting_heart_rate",
    "stress",
    "body_battery",
    "training_readiness",
)


@dataclass(frozen=True)
class ReadinessFactor:
    name: str
    status: str
    summary: str
    source_files: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReadinessSummary:
    client_id: Optional[str]
    status: str
    generated_at: datetime
    factors: list[ReadinessFactor]
    warnings: list[str]


def build_readiness_summary(db: Session, *, coach_id: str, client_id: Optional[str] = None) -> ReadinessSummary:
    overview = build_activity_overview(db, coach_id=coach_id, client_id=client_id)
    activities = _load_coach_activities(db, coach_id=coach_id, client_id=client_id)
    activity_source_files = _source_files(activities)
    latest_training_readiness = _latest_training_readiness(db, coach_id=coach_id, client_id=client_id)

    factors = [
        _activity_history_factor(overview.activity_count, activity_source_files),
        _running_consistency_factor(overview.running_summary.activity_count, overview.running_summary.active_weeks),
        _training_readiness_factor(latest_training_readiness),
        _recovery_data_factor(latest_training_readiness),
        _data_quality_factor(overview.missing_data_warnings),
    ]
    warnings = _warnings(factors, overview.missing_data_warnings)

    return ReadinessSummary(
        client_id=client_id,
        status=_overall_status(factors),
        generated_at=datetime.now(timezone.utc),
        factors=factors,
        warnings=warnings,
    )


def _load_coach_activities(db: Session, *, coach_id: str, client_id: Optional[str]) -> list[Activity]:
    query = select(Activity).join(Client, Activity.client_id == Client.id).where(Client.coach_id == coach_id)
    if client_id is not None:
        query = query.where(Activity.client_id == client_id)
    return list(db.scalars(query.order_by(Activity.start_time_gmt, Activity.created_at)))


def _latest_training_readiness(
    db: Session,
    *,
    coach_id: str,
    client_id: Optional[str],
) -> Optional[TrainingReadinessMetric]:
    query = (
        select(TrainingReadinessMetric)
        .join(Client, TrainingReadinessMetric.client_id == Client.id)
        .where(Client.coach_id == coach_id)
    )
    if client_id is not None:
        query = query.where(TrainingReadinessMetric.client_id == client_id)
    query = query.order_by(TrainingReadinessMetric.calendar_date.desc(), TrainingReadinessMetric.created_at.desc())
    return db.scalar(query.limit(1))


def _activity_history_factor(activity_count: int, source_files: list[str]) -> ReadinessFactor:
    if activity_count == 0:
        return ReadinessFactor(
            name="activity_history",
            status="yellow",
            summary="No activity history is available for this scope.",
            source_files=[],
            missing_inputs=["activities"],
        )

    return ReadinessFactor(
        name="activity_history",
        status="green",
        summary=f"{activity_count} normalized activities are available for activity-based readiness context.",
        source_files=source_files,
    )


def _running_consistency_factor(running_count: int, active_weeks: int) -> ReadinessFactor:
    if running_count == 0:
        return ReadinessFactor(
            name="running_consistency",
            status="yellow",
            summary="No running activities are available, so running consistency cannot be assessed.",
            missing_inputs=["running_activities"],
        )
    if active_weeks < 2:
        return ReadinessFactor(
            name="running_consistency",
            status="yellow",
            summary="Running history exists, but there is not enough week-over-week data for a stable trend.",
        )

    return ReadinessFactor(
        name="running_consistency",
        status="green",
        summary=f"Running appears across {active_weeks} active weeks.",
    )


def _training_readiness_factor(metric: Optional[TrainingReadinessMetric]) -> ReadinessFactor:
    if metric is None:
        return ReadinessFactor(
            name="training_readiness",
            status="yellow",
            summary="Garmin training readiness has not been imported yet.",
            missing_inputs=["training_readiness"],
        )

    return ReadinessFactor(
        name="training_readiness",
        status=_status_from_training_readiness(metric.level, metric.score),
        summary=(
            f"Latest Garmin training readiness is {metric.level} "
            f"with score {metric.score} on {metric.calendar_date.isoformat()}."
        ),
        source_files=[metric.source_file],
    )


def _recovery_data_factor(metric: Optional[TrainingReadinessMetric]) -> ReadinessFactor:
    if metric is not None:
        return ReadinessFactor(
            name="recovery_data",
            status="green",
            summary="Garmin training readiness provides a source-attributed recovery signal. Detailed sleep and health imports can add more context later.",
            source_files=[metric.source_file],
            missing_inputs=["sleep_detail", "health_status_detail"],
        )

    return ReadinessFactor(
        name="recovery_data",
        status="yellow",
        summary="Recovery data has not been imported yet, so readiness cannot include sleep, HRV, stress, Body Battery, or Garmin readiness inputs.",
        missing_inputs=list(RECOVERY_INPUTS),
    )


def _data_quality_factor(missing_data_warnings: list[str]) -> ReadinessFactor:
    if missing_data_warnings:
        return ReadinessFactor(
            name="data_quality",
            status="yellow",
            summary="Some activity fields are missing, so readiness should be treated as limited.",
            missing_inputs=["complete_activity_fields"],
        )

    return ReadinessFactor(
        name="data_quality",
        status="green",
        summary="No activity data quality warnings were detected for this scope.",
    )


def _overall_status(factors: list[ReadinessFactor]) -> str:
    if any(factor.status == "red" for factor in factors):
        return "red"
    if any(factor.status == "yellow" for factor in factors):
        return "yellow"
    return "green"


def _status_from_training_readiness(level: str, score: int) -> str:
    normalized_level = level.upper()
    if normalized_level in {"POOR", "LOW"} or score < 40:
        return "red"
    if normalized_level in {"MODERATE", "MEDIUM"} or score < 70:
        return "yellow"
    return "green"


def _source_files(activities: list[Activity]) -> list[str]:
    return sorted({activity.source_file for activity in activities if activity.source_file})


def _warnings(factors: list[ReadinessFactor], activity_warnings: list[str]) -> list[str]:
    warnings = list(activity_warnings)
    for factor in factors:
        if factor.name == "recovery_data" and "training_readiness" in factor.missing_inputs:
            warnings.append("Recovery inputs are missing, so this readiness status is activity-only and conservative.")
        if factor.name == "recovery_data" and "training_readiness" not in factor.missing_inputs:
            warnings.append("Detailed sleep and health-status records have not been imported yet.")
    return warnings
