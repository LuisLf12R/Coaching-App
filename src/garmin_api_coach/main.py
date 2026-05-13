from fastapi import FastAPI

from garmin_api_coach.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="GarminAPICoach",
        version="0.1.0",
        description="Coach-side backend for athlete data ingestion and analysis.",
    )
    app.include_router(health_router)
    return app


app = create_app()
