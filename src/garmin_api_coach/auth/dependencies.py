from fastapi import HTTPException, Request, status

from garmin_api_coach.auth.schemas import AuthenticatedCoach


def get_current_coach(request: Request) -> AuthenticatedCoach:
    settings = request.app.state.settings

    if not settings.is_local_auth_allowed():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )

    return AuthenticatedCoach(
        coach_id=settings.development_coach_id,
        email=settings.development_coach_email,
        display_name=settings.development_coach_display_name,
        auth_provider="local",
    )
