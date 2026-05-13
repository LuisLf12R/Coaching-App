from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ClientCreate(BaseModel):
    display_name: str
    sport_focus: Optional[str] = None
    goals: Optional[str] = None
    injury_notes: Optional[str] = None
    training_constraints: Optional[str] = None
    coach_notes: Optional[str] = None


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    coach_id: str
    display_name: str
    sport_focus: Optional[str]
    goals: Optional[str]
    injury_notes: Optional[str]
    training_constraints: Optional[str]
    coach_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    provider: str
    source_activity_id: str
    source_file: Optional[str]
    activity_type: str
    sport_type: Optional[str]
    start_time_gmt: Optional[datetime]
    start_time_local: Optional[datetime]
    duration_seconds: Optional[float]
    distance_meters: Optional[float]
    avg_speed_meters_per_second: Optional[float]
    avg_hr: Optional[int]
    max_hr: Optional[int]
    calories: Optional[float]
    steps: Optional[int]
    training_effect_label: Optional[str]
    activity_training_load: Optional[float]
    provider_metadata: Optional[dict[str, object]]


class ActivityTypeSummary(BaseModel):
    activity_type: str
    sport_type: Optional[str]
    activity_count: int
    total_duration_seconds: Optional[float]
    total_distance_meters: Optional[float]


class ActivityPeriodSummary(BaseModel):
    period: str
    activity_type: str
    sport_type: Optional[str]
    activity_count: int
    total_duration_seconds: Optional[float]
    total_distance_meters: Optional[float]


class ActivityFocusSummaryRead(BaseModel):
    activity_count: int
    active_weeks: int
    total_duration_seconds: Optional[float]
    total_distance_meters: Optional[float]
    missing_duration_count: int
    missing_distance_count: int


class ActivityOverviewRead(BaseModel):
    client_id: Optional[str]
    activity_count: int
    first_activity_at: Optional[datetime]
    last_activity_at: Optional[datetime]
    active_days: int
    active_weeks: int
    sport_mix: list[ActivityTypeSummary]
    weekly_activity_counts: list[ActivityPeriodSummary]
    monthly_activity_counts: list[ActivityPeriodSummary]
    running_summary: ActivityFocusSummaryRead
    strength_summary: ActivityFocusSummaryRead
    missing_data_warnings: list[str]
