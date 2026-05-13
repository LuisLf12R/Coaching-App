from fastapi import APIRouter, Depends

from garmin_api_coach.auth.dependencies import get_current_coach
from garmin_api_coach.auth.schemas import AuthenticatedCoach

router = APIRouter(tags=["auth"])


@router.get("/me")
def read_current_coach(
    current_coach: AuthenticatedCoach = Depends(get_current_coach),
) -> AuthenticatedCoach:
    return current_coach
