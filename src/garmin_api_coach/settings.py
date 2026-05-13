from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


Environment = Literal["development", "test", "production"]


class Settings(BaseSettings):
    app_name: str = "GarminAPICoach"
    app_version: str = "0.1.0"
    app_description: str = "Coach-side backend for athlete data ingestion and analysis."
    environment: Environment = "development"
    debug: bool = False
    database_url: str = (
        "postgresql+psycopg://garmin_api_coach:garmin_api_coach"
        "@localhost:5432/garmin_api_coach_dev"
    )
    local_auth_bypass_enabled: bool = True
    development_coach_id: str = "Luis-dev-coach"
    development_coach_email: str = "luisrivglez@gmail.com"
    development_coach_display_name: str = "Luis"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GARMIN_API_COACH_",
        extra="ignore",
    )

    def is_local_auth_allowed(self) -> bool:
        return self.environment in {"development", "test"} and self.local_auth_bypass_enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()
