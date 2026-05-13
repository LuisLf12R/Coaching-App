from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from garmin_api_coach.analytics.activity_overview import build_activity_overview
from garmin_api_coach.api.coaches import get_or_create_coach
from garmin_api_coach.api.schemas import ActivityOverviewRead
from garmin_api_coach.auth.dependencies import get_current_coach
from garmin_api_coach.auth.schemas import AuthenticatedCoach
from garmin_api_coach.db.session import get_db_session

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/activity-overview", response_model=ActivityOverviewRead)
def get_activity_overview(
    client_id: Optional[str] = None,
    current_coach: AuthenticatedCoach = Depends(get_current_coach),
    db: Session = Depends(get_db_session),
):
    coach = get_or_create_coach(db, current_coach)
    return build_activity_overview(db, coach_id=coach.id, client_id=client_id)
