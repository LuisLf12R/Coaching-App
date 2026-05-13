from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from garmin_api_coach.api.coaches import get_or_create_coach
from garmin_api_coach.api.schemas import ActivityRead, ActivityTypeSummary
from garmin_api_coach.auth.dependencies import get_current_coach
from garmin_api_coach.auth.schemas import AuthenticatedCoach
from garmin_api_coach.db.models import Activity, Client
from garmin_api_coach.db.session import get_db_session

router = APIRouter(tags=["activities"])


@router.get("/activities", response_model=list[ActivityRead])
def list_activities(
    client_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    sport_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_coach: AuthenticatedCoach = Depends(get_current_coach),
    db: Session = Depends(get_db_session),
) -> list[Activity]:
    coach = get_or_create_coach(db, current_coach)
    query = _coach_activity_query(coach.id)
    if client_id is not None:
        query = query.where(Activity.client_id == client_id)
    if activity_type is not None:
        query = query.where(Activity.activity_type == activity_type)
    if sport_type is not None:
        query = query.where(Activity.sport_type == sport_type)

    query = query.order_by(Activity.start_time_gmt.desc().nullslast(), Activity.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(query))


@router.get("/activity-summaries/by-type", response_model=list[ActivityTypeSummary])
def summarize_activities_by_type(
    client_id: Optional[str] = None,
    current_coach: AuthenticatedCoach = Depends(get_current_coach),
    db: Session = Depends(get_db_session),
) -> list[ActivityTypeSummary]:
    coach = get_or_create_coach(db, current_coach)
    query = (
        select(
            Activity.activity_type,
            Activity.sport_type,
            func.count(Activity.id).label("activity_count"),
            func.sum(Activity.duration_seconds).label("total_duration_seconds"),
            func.sum(Activity.distance_meters).label("total_distance_meters"),
        )
        .join(Client, Activity.client_id == Client.id)
        .where(Client.coach_id == coach.id)
        .group_by(Activity.activity_type, Activity.sport_type)
        .order_by(Activity.activity_type, Activity.sport_type)
    )
    if client_id is not None:
        query = query.where(Activity.client_id == client_id)

    return [
        ActivityTypeSummary(
            activity_type=row.activity_type,
            sport_type=row.sport_type,
            activity_count=row.activity_count,
            total_duration_seconds=row.total_duration_seconds,
            total_distance_meters=row.total_distance_meters,
        )
        for row in db.execute(query)
    ]


def _coach_activity_query(coach_id: str) -> Select[tuple[Activity]]:
    return select(Activity).join(Client, Activity.client_id == Client.id).where(Client.coach_id == coach_id)
