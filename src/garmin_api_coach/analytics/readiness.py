from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from garmin_api_coach.analytics.activity_overview import build_activity_overview
from garmin_api_coach.db.models import (
    Activity,
    AcuteTrainingLoadMetric,
    Client,
    HealthStatusMetric,
    SleepMetric,
    TrainingReadinessMetric,
)


RECOVERY_INPUTS = (
    "sleep",
    "hrv",
    "resting_heart_rate",
    "stress",
    "body_battery",
    "training_readiness",
    "acute_training_load",
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
    latest_sleep = _latest_sleep(db, coach_id=coach_id, client_id=client_id)
    latest_health_status = _latest_health_status(db, coach_id=coach_id, client_id=client_id)
    latest_acute_training_load = _latest_acute_training_load(db, coach_id=coach_id, client_id=client_id)

    factors = [
        _activity_history_factor(overview.activity_count, activity_source_files),
        _running_consistency_factor(overview.running_summary.activity_count, overview.running_summary.active_weeks),
        _training_readiness_factor(latest_training_readiness),
        _acute_training_load_factor(latest_acute_training_load),
        _sleep_detail_factor(latest_sleep),
        _health_status_factor(latest_health_status),
        _recovery_data_factor(latest_training_readiness, latest_sleep, latest_health_status, latest_acute_training_load),
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


def _latest_sleep(
    db: Session,
    *,
    coach_id: str,
    client_id: Optional[str],
) -> Optional[SleepMetric]:
    query = select(SleepMetric).join(Client, SleepMetric.client_id == Client.id).where(Client.coach_id == coach_id)
    if client_id is not None:
        query = query.where(SleepMetric.client_id == client_id)
    query = query.order_by(SleepMetric.calendar_date.desc(), SleepMetric.created_at.desc())
    return db.scalar(query.limit(1))


def _latest_health_status(
    db: Session,
    *,
    coach_id: str,
    client_id: Optional[str],
) -> Optional[HealthStatusMetric]:
    query = (
        select(HealthStatusMetric)
        .join(Client, HealthStatusMetric.client_id == Client.id)
        .where(Client.coach_id == coach_id)
    )
    if client_id is not None:
        query = query.where(HealthStatusMetric.client_id == client_id)
    query = query.order_by(HealthStatusMetric.calendar_date.desc(), HealthStatusMetric.created_at.desc())
    return db.scalar(query.limit(1))


def _latest_acute_training_load(
    db: Session,
    *,
    coach_id: str,
    client_id: Optional[str],
) -> Optional[AcuteTrainingLoadMetric]:
    query = (
        select(AcuteTrainingLoadMetric)
        .join(Client, AcuteTrainingLoadMetric.client_id == Client.id)
        .where(Client.coach_id == coach_id)
    )
    if client_id is not None:
        query = query.where(AcuteTrainingLoadMetric.client_id == client_id)
    query = query.order_by(AcuteTrainingLoadMetric.calendar_date.desc(), AcuteTrainingLoadMetric.created_at.desc())
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


def _sleep_detail_factor(metric: Optional[SleepMetric]) -> ReadinessFactor:
    if metric is None:
        return ReadinessFactor(
            name="sleep_detail",
            status="yellow",
            summary="Detailed Garmin sleep data has not been imported yet.",
            missing_inputs=["sleep_detail"],
        )

    if metric.overall_score is None:
        return ReadinessFactor(
            name="sleep_detail",
            status="yellow",
            summary=f"Latest Garmin sleep record is available for {metric.calendar_date.isoformat()}, but it has no overall sleep score.",
            source_files=[metric.source_file],
            missing_inputs=["sleep_score"],
        )

    return ReadinessFactor(
        name="sleep_detail",
        status=_status_from_score(metric.overall_score),
        summary=f"Latest Garmin sleep score is {metric.overall_score} on {metric.calendar_date.isoformat()}.",
        source_files=[metric.source_file],
    )


def _acute_training_load_factor(metric: Optional[AcuteTrainingLoadMetric]) -> ReadinessFactor:
    if metric is None:
        return ReadinessFactor(
            name="acute_training_load",
            status="yellow",
            summary="Garmin acute training load has not been imported yet.",
            missing_inputs=["acute_training_load"],
        )

    summary_parts = []
    if metric.daily_training_load_acute is not None:
        summary_parts.append(f"acute load {metric.daily_training_load_acute:g}")
    if metric.daily_training_load_chronic is not None:
        summary_parts.append(f"chronic load {metric.daily_training_load_chronic:g}")
    if metric.daily_acute_chronic_workload_ratio is not None:
        summary_parts.append(f"ACWR {metric.daily_acute_chronic_workload_ratio:g}")

    if summary_parts:
        summary = (
            f"Latest Garmin acute training load on {metric.calendar_date.isoformat()} shows "
            f"{', '.join(summary_parts)}."
        )
    else:
        summary = (
            f"Latest Garmin acute training load record is available for {metric.calendar_date.isoformat()}, "
            "but load values were not present."
        )

    if metric.acwr_status:
        summary = f"{summary} Garmin ACWR status is {metric.acwr_status}."

    return ReadinessFactor(
        name="acute_training_load",
        status=_status_from_acwr_status(metric.acwr_status),
        summary=summary,
        source_files=[metric.source_file],
    )


def _health_status_factor(metric: Optional[HealthStatusMetric]) -> ReadinessFactor:
    if metric is None:
        return ReadinessFactor(
            name="health_status_detail",
            status="yellow",
            summary="Detailed Garmin health-status data has not been imported yet.",
            missing_inputs=["health_status_detail"],
        )

    summary_parts = []
    if metric.hrv_value is not None:
        summary_parts.append(f"HRV {metric.hrv_value:g}")
    if metric.heart_rate_value is not None:
        summary_parts.append(f"heart rate {metric.heart_rate_value:g}")
    if metric.respiration_value is not None:
        summary_parts.append(f"respiration {metric.respiration_value:g}")

    if summary_parts:
        summary = (
            f"Latest Garmin health-status record on {metric.calendar_date.isoformat()} includes "
            f"{', '.join(summary_parts)}."
        )
    else:
        summary = (
            f"Latest Garmin health-status record is available for {metric.calendar_date.isoformat()}, "
            "but core recovery values were not present."
        )

    return ReadinessFactor(
        name="health_status_detail",
        status=_status_from_health_status(metric),
        summary=summary,
        source_files=[metric.source_file],
    )


def _recovery_data_factor(
    training_readiness: Optional[TrainingReadinessMetric],
    sleep: Optional[SleepMetric],
    health_status: Optional[HealthStatusMetric],
    acute_training_load: Optional[AcuteTrainingLoadMetric],
) -> ReadinessFactor:
    source_files = []
    missing_inputs = []
    if training_readiness is not None:
        source_files.append(training_readiness.source_file)
    else:
        missing_inputs.append("training_readiness")
    if sleep is not None:
        source_files.append(sleep.source_file)
    else:
        missing_inputs.append("sleep_detail")
    if health_status is not None:
        source_files.append(health_status.source_file)
    else:
        missing_inputs.append("health_status_detail")
    if acute_training_load is not None:
        source_files.append(acute_training_load.source_file)
    else:
        missing_inputs.append("acute_training_load")

    if training_readiness is not None or sleep is not None or health_status is not None or acute_training_load is not None:
        return ReadinessFactor(
            name="recovery_data",
            status="green",
            summary="Imported Garmin recovery and load records provide source-attributed readiness context.",
            source_files=sorted(set(source_files)),
            missing_inputs=missing_inputs,
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


def _status_from_score(score: int) -> str:
    if score < 40:
        return "red"
    if score < 70:
        return "yellow"
    return "green"


def _status_from_acwr_status(status: Optional[str]) -> str:
    if status is None:
        return "yellow"
    normalized_status = status.upper()
    if normalized_status == "HIGH":
        return "red"
    if normalized_status in {"LOW", "NONE", "UNKNOWN"}:
        return "yellow"
    return "green"


def _status_from_health_status(metric: HealthStatusMetric) -> str:
    statuses = {
        status.upper()
        for status in (
            metric.heart_rate_status,
            metric.hrv_status,
            metric.respiration_status,
            metric.spo2_status,
            metric.skin_temp_c_status,
        )
        if status
    }
    if statuses & {"LOW", "HIGH", "ABNORMAL", "POOR"}:
        return "red"
    if statuses & {"ONBOARDING", "UNKNOWN"}:
        return "yellow"
    return "green"


def _source_files(activities: list[Activity]) -> list[str]:
    return sorted({activity.source_file for activity in activities if activity.source_file})


def _warnings(factors: list[ReadinessFactor], activity_warnings: list[str]) -> list[str]:
    warnings = list(activity_warnings)
    for factor in factors:
        if factor.name != "recovery_data":
            continue
        missing_inputs = set(factor.missing_inputs)
        if not factor.source_files:
            warnings.append("Recovery inputs are missing, so this readiness status is activity-only and conservative.")
            continue
        if "training_readiness" in missing_inputs:
            warnings.append("Garmin training readiness records have not been imported yet.")
        if "sleep_detail" in missing_inputs:
            warnings.append("Detailed sleep records have not been imported yet.")
        if "health_status_detail" in missing_inputs:
            warnings.append("Detailed health-status records have not been imported yet.")
        if "acute_training_load" in missing_inputs:
            warnings.append("Garmin acute training load records have not been imported yet.")
    return warnings
