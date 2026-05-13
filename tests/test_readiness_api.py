from datetime import datetime, timezone
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from garmin_api_coach.db import models  # noqa: F401
from garmin_api_coach.db.base import Base
from garmin_api_coach.db.models import Activity, Client, Coach, DataImport, TrainingReadinessMetric
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


def test_readiness_summary_is_activity_only_and_conservative() -> None:
    api, db = _test_client()
    client = _seed_running_history(db)

    response = api.get("/readiness/summary", params={"client_id": client.id})

    assert response.status_code == 200
    payload = response.json()
    factors = {factor["name"]: factor for factor in payload["factors"]}

    assert payload["client_id"] == client.id
    assert payload["status"] == "yellow"
    assert factors["activity_history"]["status"] == "green"
    assert factors["activity_history"]["source_files"] == [
        "DI_CONNECT/DI-Connect-Fitness/luis_0_summarizedActivities.json"
    ]
    assert factors["running_consistency"]["status"] == "green"
    assert factors["recovery_data"]["status"] == "yellow"
    assert factors["recovery_data"]["missing_inputs"] == [
        "sleep",
        "hrv",
        "resting_heart_rate",
        "stress",
        "body_battery",
        "training_readiness",
    ]
    assert "Recovery inputs are missing" in payload["warnings"][-1]


def test_readiness_summary_reports_missing_activity_history() -> None:
    api, db = _test_client()
    client = _seed_empty_client(db)

    response = api.get("/readiness/summary", params={"client_id": client.id})

    assert response.status_code == 200
    payload = response.json()
    factors = {factor["name"]: factor for factor in payload["factors"]}

    assert payload["status"] == "yellow"
    assert factors["activity_history"]["missing_inputs"] == ["activities"]
    assert "No activities found for the selected scope." in payload["warnings"]


def test_readiness_summary_uses_latest_training_readiness_metric() -> None:
    api, db = _test_client()
    client = _seed_running_history(db)
    data_import = db.scalar(select(DataImport).where(DataImport.client_id == client.id))
    assert data_import is not None
    db.add(
        TrainingReadinessMetric(
            client_id=client.id,
            data_import_id=data_import.id,
            provider="garmin",
            source_file="DI_CONNECT/DI-Connect-Metrics/TrainingReadinessDTO_20260217_20260528_116034249.json",
            source_record_id="2026-05-12",
            calendar_date=datetime(2026, 5, 12, tzinfo=timezone.utc).date(),
            level="LOW",
            score=36,
            sleep_score=84,
            hrv_weekly_average=50.0,
            acute_load=680,
        )
    )
    db.commit()

    response = api.get("/readiness/summary", params={"client_id": client.id})

    assert response.status_code == 200
    payload = response.json()
    factors = {factor["name"]: factor for factor in payload["factors"]}

    assert payload["status"] == "red"
    assert factors["training_readiness"]["status"] == "red"
    assert factors["training_readiness"]["source_files"] == [
        "DI_CONNECT/DI-Connect-Metrics/TrainingReadinessDTO_20260217_20260528_116034249.json"
    ]
    assert "score 36" in factors["training_readiness"]["summary"]
    assert factors["recovery_data"]["status"] == "green"
    assert factors["recovery_data"]["missing_inputs"] == ["sleep_detail", "health_status_detail"]


def _seed_empty_client(db: Session) -> Client:
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
    db.commit()
    db.refresh(client)
    return client


def _seed_running_history(db: Session) -> Client:
    client = _seed_empty_client(db)
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
    db.add_all(
        [
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
            ),
            Activity(
                client_id=client.id,
                data_import_id=data_import.id,
                provider="garmin",
                source_activity_id="garmin-activity-2",
                source_file="DI_CONNECT/DI-Connect-Fitness/luis_0_summarizedActivities.json",
                activity_type="running",
                sport_type="RUNNING",
                start_time_gmt=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc),
                start_time_local=datetime(2026, 5, 8, 6, 0, tzinfo=timezone.utc),
                duration_seconds=1900.0,
                distance_meters=5200.0,
            ),
        ]
    )
    db.commit()
    db.refresh(client)
    return client
