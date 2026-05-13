from fastapi.testclient import TestClient

from garmin_api_coach.main import create_app
from garmin_api_coach.settings import get_settings


def test_me_returns_development_coach_when_local_auth_is_allowed() -> None:
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get("/me")

    assert response.status_code == 200
    assert response.json() == {
        "coach_id": "Luis-dev-coach",
        "email": "luisrivglez@gmail.com",
        "display_name": "Luis",
        "auth_provider": "local",
    }


def test_me_requires_authentication_when_environment_is_production(monkeypatch) -> None:
    monkeypatch.setenv("GARMIN_API_COACH_ENVIRONMENT", "production")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get("/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication is required."}

    get_settings.cache_clear()


def test_me_requires_authentication_when_local_bypass_is_disabled(monkeypatch) -> None:
    monkeypatch.setenv("GARMIN_API_COACH_LOCAL_AUTH_BYPASS_ENABLED", "false")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get("/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication is required."}

    get_settings.cache_clear()
