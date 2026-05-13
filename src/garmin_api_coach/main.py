from fastapi import FastAPI

from garmin_api_coach.api.health import router as health_router
from garmin_api_coach.api.me import router as me_router
from garmin_api_coach.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        debug=settings.debug,
    )
    app.state.settings = settings
    app.include_router(health_router)
    app.include_router(me_router)
    return app


app = create_app()
