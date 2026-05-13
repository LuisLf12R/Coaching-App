from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Optional, Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from garmin_api_coach.db.models import Activity, Client


@dataclass(frozen=True)
class ActivityBucket:
    period: str
    activity_type: str
    sport_type: Optional[str]
    activity_count: int
    total_duration_seconds: Optional[float]
    total_distance_meters: Optional[float]


@dataclass(frozen=True)
class ActivitySportMixItem:
    activity_type: str
    sport_type: Optional[str]
    activity_count: int
    total_duration_seconds: Optional[float]
    total_distance_meters: Optional[float]


@dataclass(frozen=True)
class ActivityFocusSummary:
    activity_count: int
    active_weeks: int
    total_duration_seconds: Optional[float]
    total_distance_meters: Optional[float]
    missing_duration_count: int
    missing_distance_count: int


@dataclass(frozen=True)
class ActivityOverview:
    client_id: Optional[str]
    activity_count: int
    first_activity_at: Optional[datetime]
    last_activity_at: Optional[datetime]
    active_days: int
    active_weeks: int
    sport_mix: list[ActivitySportMixItem] = field(default_factory=list)
    weekly_activity_counts: list[ActivityBucket] = field(default_factory=list)
    monthly_activity_counts: list[ActivityBucket] = field(default_factory=list)
    running_summary: ActivityFocusSummary = field(default_factory=lambda: _empty_focus_summary())
    strength_summary: ActivityFocusSummary = field(default_factory=lambda: _empty_focus_summary())
    missing_data_warnings: list[str] = field(default_factory=list)


def build_activity_overview(db: Session, *, coach_id: str, client_id: Optional[str] = None) -> ActivityOverview:
    activities = _load_coach_activities(db, coach_id=coach_id, client_id=client_id)
    first_activity_at = _min_activity_time(activities)
    last_activity_at = _max_activity_time(activities)
    dated_activities = [activity for activity in activities if activity.start_time_gmt is not None]

    missing_data_warnings = _missing_data_warnings(activities)

    return ActivityOverview(
        client_id=client_id,
        activity_count=len(activities),
        first_activity_at=first_activity_at,
        last_activity_at=last_activity_at,
        active_days=len({activity.start_time_gmt.date() for activity in dated_activities}),
        active_weeks=len({_week_period(activity.start_time_gmt) for activity in dated_activities}),
        sport_mix=_sport_mix(activities),
        weekly_activity_counts=_period_buckets(activities, period="week"),
        monthly_activity_counts=_period_buckets(activities, period="month"),
        running_summary=_focus_summary(activities, "running"),
        strength_summary=_focus_summary(activities, "strength"),
        missing_data_warnings=missing_data_warnings,
    )


def _load_coach_activities(db: Session, *, coach_id: str, client_id: Optional[str]) -> list[Activity]:
    query = select(Activity).join(Client, Activity.client_id == Client.id).where(Client.coach_id == coach_id)
    if client_id is not None:
        query = query.where(Activity.client_id == client_id)
    query = query.order_by(Activity.start_time_gmt, Activity.created_at)
    return list(db.scalars(query))


def _sport_mix(activities: list[Activity]) -> list[ActivitySportMixItem]:
    totals: dict[tuple[str, Optional[str]], dict[str, Union[Optional[float], int]]] = defaultdict(_empty_totals)
    for activity in activities:
        key = (activity.activity_type, activity.sport_type)
        _add_activity_to_totals(totals[key], activity)

    return [
        ActivitySportMixItem(
            activity_type=activity_type,
            sport_type=sport_type,
            activity_count=int(total["activity_count"] or 0),
            total_duration_seconds=total["total_duration_seconds"],
            total_distance_meters=total["total_distance_meters"],
        )
        for (activity_type, sport_type), total in sorted(totals.items(), key=_activity_sort_key)
    ]


def _period_buckets(activities: list[Activity], *, period: str) -> list[ActivityBucket]:
    totals: dict[tuple[str, str, Optional[str]], dict[str, Union[Optional[float], int]]] = defaultdict(_empty_totals)
    for activity in activities:
        if activity.start_time_gmt is None:
            continue
        period_key = _month_period(activity.start_time_gmt) if period == "month" else _week_period(activity.start_time_gmt)
        key = (period_key, activity.activity_type, activity.sport_type)
        _add_activity_to_totals(totals[key], activity)

    return [
        ActivityBucket(
            period=period_key,
            activity_type=activity_type,
            sport_type=sport_type,
            activity_count=int(total["activity_count"] or 0),
            total_duration_seconds=total["total_duration_seconds"],
            total_distance_meters=total["total_distance_meters"],
        )
        for (period_key, activity_type, sport_type), total in sorted(totals.items(), key=_period_sort_key)
    ]


def _focus_summary(activities: list[Activity], focus_type: str) -> ActivityFocusSummary:
    focused = [activity for activity in activities if activity.activity_type == focus_type]
    dated = [activity for activity in focused if activity.start_time_gmt is not None]
    total_duration = _sum_or_none(activity.duration_seconds for activity in focused)
    total_distance = _sum_or_none(activity.distance_meters for activity in focused)

    return ActivityFocusSummary(
        activity_count=len(focused),
        active_weeks=len({_week_period(activity.start_time_gmt) for activity in dated}),
        total_duration_seconds=total_duration,
        total_distance_meters=total_distance,
        missing_duration_count=sum(1 for activity in focused if activity.duration_seconds is None),
        missing_distance_count=sum(1 for activity in focused if activity.distance_meters is None),
    )


def _missing_data_warnings(activities: list[Activity]) -> list[str]:
    warnings = []
    if not activities:
        return ["No activities found for the selected scope."]
    if any(activity.start_time_gmt is None for activity in activities):
        warnings.append("Some activities are missing a start time and are excluded from weekly and monthly trends.")
    if any(activity.duration_seconds is None for activity in activities):
        warnings.append("Some activities are missing duration, so duration totals may be incomplete.")
    if any(activity.distance_meters is None for activity in activities):
        warnings.append("Some activities are missing distance, so distance totals may be incomplete.")
    if not any(activity.activity_type == "running" for activity in activities):
        warnings.append("No running activities found in the selected scope.")
    return warnings


def _add_activity_to_totals(total: dict[str, Union[Optional[float], int]], activity: Activity) -> None:
    total["activity_count"] = int(total["activity_count"] or 0) + 1
    if activity.duration_seconds is not None:
        total["total_duration_seconds"] = float(total["total_duration_seconds"] or 0.0) + activity.duration_seconds
    if activity.distance_meters is not None:
        total["total_distance_meters"] = float(total["total_distance_meters"] or 0.0) + activity.distance_meters


def _empty_totals() -> dict[str, Union[Optional[float], int]]:
    return {
        "activity_count": 0,
        "total_duration_seconds": None,
        "total_distance_meters": None,
    }


def _empty_focus_summary() -> ActivityFocusSummary:
    return ActivityFocusSummary(
        activity_count=0,
        active_weeks=0,
        total_duration_seconds=None,
        total_distance_meters=None,
        missing_duration_count=0,
        missing_distance_count=0,
    )


def _activity_sort_key(item: tuple[tuple[str, Optional[str]], dict[str, Union[Optional[float], int]]]) -> tuple[str, str]:
    (activity_type, sport_type), _total = item
    return activity_type, sport_type or ""


def _period_sort_key(
    item: tuple[tuple[str, str, Optional[str]], dict[str, Union[Optional[float], int]]],
) -> tuple[str, str, str]:
    (period_key, activity_type, sport_type), _total = item
    return period_key, activity_type, sport_type or ""


def _month_period(value: datetime) -> str:
    return value.strftime("%Y-%m")


def _week_period(value: datetime) -> str:
    start_of_week = value.date() - timedelta(days=value.weekday())
    return start_of_week.isoformat()


def _min_activity_time(activities: list[Activity]) -> Optional[datetime]:
    values = [activity.start_time_gmt for activity in activities if activity.start_time_gmt is not None]
    return min(values) if values else None


def _max_activity_time(activities: list[Activity]) -> Optional[datetime]:
    values = [activity.start_time_gmt for activity in activities if activity.start_time_gmt is not None]
    return max(values) if values else None


def _sum_or_none(values: Iterable[Optional[float]]) -> Optional[float]:
    numbers = [value for value in values if value is not None]
    return float(sum(numbers)) if numbers else None
