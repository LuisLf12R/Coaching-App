from datetime import datetime, timezone
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from garmin_api_coach.db.base import Base
from garmin_api_coach.db import models  # noqa: F401
from garmin_api_coach.db.models import Activity, Client, Coach, DataImport
from garmin_api_coach.db.session import get_db_session
from garmin_api_coach.main import create_app


def _test_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    app = create_app()

    def override_db_session() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db_session] = override_db_session
    return TestClient(app), db


def test_clients_api_creates_and_lists_placeholder_client() -> None:
    api, _db = _test_client()

    create_response = api.post(
        "/clients",
        json={
            "display_name": "Placeholder Athlete",
            "sport_focus": "running",
        },
    )
    list_response = api.get("/clients")

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["display_name"] == "Placeholder Athlete"
    assert created["coach_id"] == "Luis-dev-coach"
    assert list_response.status_code == 200
    assert [client["id"] for client in list_response.json()] == [created["id"]]


def test_activities_api_lists_coach_owned_activities_and_summarizes_by_type() -> None:
    api, db = _test_client()
    client = _seed_activity(db)

    list_response = api.get("/activities", params={"client_id": client.id})
    summary_response = api.get("/activity-summaries/by-type", params={"client_id": client.id})

    assert list_response.status_code == 200
    activities = list_response.json()
    assert len(activities) == 1
    assert activities[0]["source_activity_id"] == "garmin-activity-1"
    assert activities[0]["distance_meters"] == 5000.0

    assert summary_response.status_code == 200
    assert summary_response.json() == [
        {
            "activity_type": "running",
            "sport_type": "RUNNING",
            "activity_count": 1,
            "total_duration_seconds": 1800.0,
            "total_distance_meters": 5000.0,
        }
    ]


def _seed_activity(db: Session) -> Client:
    coach = Coach(
        id="Luis-dev-coach",
        email="luisrivglez@gmail.com",
        display_name="Luis",
        auth_provider="local",
    )
    client = Client(
        coach_id=coach.id,
        display_name="Placeholder Athlete",
        sport_focus="running",
    )
    db.add_all([coach, client])
    db.flush()
    data_import = DataImport(
        client_id=client.id,
        provider="garmin",
        source_name="garmin-export.zip",
        source_type="garmin_export_zip",
        parser_version="test",
        status="completed",
    )
    db.add(data_import)
    db.flush()
    db.add(
        Activity(
            client_id=client.id,
            data_import_id=data_import.id,
            provider="garmin",
            source_activity_id="garmin-activity-1",
            source_file="DI_CONNECT/DI-Connect-Fitness/luis_0_summarizedActivities.json",
            activity_type="running",
            sport_type="RUNNING",
            start_time_gmt=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
            start_time_local=datetime(2026, 5, 1, 6, 0, tzinfo=timezone.utc),
            duration_seconds=1800.0,
            distance_meters=5000.0,
            provider_metadata={"elapsedDuration": 1810.0},
        )
    )
    db.commit()
    db.refresh(client)
    return client
