from garmin_api_coach.settings import Settings


def test_settings_defaults_are_local_safe() -> None:
    settings = Settings()

    assert settings.app_name == "GarminAPICoach"
    assert settings.environment == "development"
    assert settings.debug is False
    assert "garmin_api_coach_dev" in settings.database_url
    assert settings.local_auth_bypass_enabled is True
    assert settings.development_coach_id == "Luis-dev-coach"
    assert settings.development_coach_email == "luisrivglez@gmail.com"
    assert settings.development_coach_display_name == "Luis"
    assert settings.is_local_auth_allowed() is True


def test_settings_load_prefixed_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("GARMIN_API_COACH_ENVIRONMENT", "test")
    monkeypatch.setenv("GARMIN_API_COACH_DEBUG", "true")
    monkeypatch.setenv("GARMIN_API_COACH_APP_NAME", "TestCoach")

    settings = Settings()

    assert settings.environment == "test"
    assert settings.debug is True
    assert settings.app_name == "TestCoach"


def test_local_auth_is_not_allowed_in_production_by_default() -> None:
    settings = Settings(environment="production")

    assert settings.local_auth_bypass_enabled is True
    assert settings.is_local_auth_allowed() is False


def test_local_auth_can_be_disabled_in_development() -> None:
    settings = Settings(local_auth_bypass_enabled=False)

    assert settings.environment == "development"
    assert settings.is_local_auth_allowed() is False
