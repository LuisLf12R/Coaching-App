from sqlalchemy.orm import Session

from garmin_api_coach.auth.schemas import AuthenticatedCoach
from garmin_api_coach.db.models import Coach


def get_or_create_coach(db: Session, authenticated_coach: AuthenticatedCoach) -> Coach:
    coach = db.get(Coach, authenticated_coach.coach_id)
    if coach is not None:
        return coach

    coach = Coach(
        id=authenticated_coach.coach_id,
        email=authenticated_coach.email,
        display_name=authenticated_coach.display_name,
        auth_provider=authenticated_coach.auth_provider,
    )
    db.add(coach)
    db.commit()
    db.refresh(coach)
    return coach
