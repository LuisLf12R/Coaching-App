from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from garmin_api_coach.analytics.readiness import build_readiness_summary
from garmin_api_coach.api.coaches import get_or_create_coach
from garmin_api_coach.api.schemas import ReadinessSummaryRead
from garmin_api_coach.auth.dependencies import get_current_coach
from garmin_api_coach.auth.schemas import AuthenticatedCoach
from garmin_api_coach.db.session import get_db_session

router = APIRouter(prefix="/readiness", tags=["readiness"])


@router.get("/summary", response_model=ReadinessSummaryRead)
def get_readiness_summary(
    client_id: Optional[str] = None,
    current_coach: AuthenticatedCoach = Depends(get_current_coach),
    db: Session = Depends(get_db_session),
):
    coach = get_or_create_coach(db, current_coach)
    return build_readiness_summary(db, coach_id=coach.id, client_id=client_id)
