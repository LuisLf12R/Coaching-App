import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from garmin_api_coach.db.base import Base
from garmin_api_coach.db import models  # noqa: F401
from garmin_api_coach.db.models import Activity, Client, Coach, DataImport, RawRecord
from garmin_api_coach.imports.garmin_summarized_activities import (
    GarminActivityImportError,
    import_garmin_summarized_activities,
)


LOCAL_GARMIN_EXPORT = Path("data/raw/642bffa2-69d5-466c-9599-eb82c5e5124b_1.zip")


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _create_placeholder_client(db: Session) -> Client:
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


def _write_export_zip(export_zip: Path, *, distance: float) -> None:
    source_file = "DI_CONNECT/DI-Connect-Fitness/luis_0_summarizedActivities.json"
    payload = [
        {
            "summarizedActivitiesExport": [
                {
                    "activityId": "garmin-activity-1",
                    "activityType": "running",
                    "sportType": "RUNNING",
                    "startTimeGmt": "2026-05-01 12:00:00",
                    "startTimeLocal": "2026-05-01 06:00:00",
                    "duration": 1800.0,
                    "distance": distance,
                    "avgSpeed": 2.77,
                    "avgHr": 145,
                    "maxHr": 178,
                    "calories": 420.0,
                    "activityTrainingLoad": 72.5,
                    "elapsedDuration": 1810.0,
                }
            ]
        }
    ]
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps(payload))


def test_import_creates_activity_level_raw_records_and_normalized_activities(tmp_path: Path) -> None:
    db = _session()
    client = _create_placeholder_client(db)
    export_zip = tmp_path / "garmin-export.zip"
    _write_export_zip(export_zip, distance=5000.0)

    summary = import_garmin_summarized_activities(db, client_id=client.id, source_path=export_zip)

    assert summary.records_seen == 1
    assert summary.records_parsed == 1
    assert summary.raw_records_created == 1
    assert summary.activities_inserted == 1
    assert summary.activities_updated == 0

    data_import = db.get(DataImport, summary.data_import_id)
    raw_record = db.scalar(select(RawRecord))
    activity = db.scalar(select(Activity))

    assert data_import is not None
    assert data_import.summary["activities_inserted"] == 1
    assert raw_record is not None
    assert raw_record.source_record_id == "garmin-activity-1"
    assert raw_record.payload["distance"] == 5000.0
    assert activity is not None
    assert activity.client_id == client.id
    assert activity.source_activity_id == "garmin-activity-1"
    assert activity.distance_meters == 5000.0
    assert activity.provider_metadata == {"elapsedDuration": 1810.0}


def test_import_upserts_duplicate_activity_and_preserves_new_raw_record(tmp_path: Path) -> None:
    db = _session()
    client = _create_placeholder_client(db)
    export_zip = tmp_path / "garmin-export.zip"

    _write_export_zip(export_zip, distance=5000.0)
    first_summary = import_garmin_summarized_activities(db, client_id=client.id, source_path=export_zip)

    _write_export_zip(export_zip, distance=5500.0)
    second_summary = import_garmin_summarized_activities(db, client_id=client.id, source_path=export_zip)

    activity = db.scalar(select(Activity))

    assert first_summary.activities_inserted == 1
    assert second_summary.activities_inserted == 0
    assert second_summary.activities_updated == 1
    assert db.scalar(select(func.count(DataImport.id))) == 2
    assert len(list(db.scalars(select(DataImport)))) == 2
    assert len(list(db.scalars(select(RawRecord)))) == 2
    assert len(list(db.scalars(select(Activity)))) == 1
    assert activity is not None
    assert activity.distance_meters == 5500.0
    assert activity.data_import_id == second_summary.data_import_id


def test_import_rejects_missing_client(tmp_path: Path) -> None:
    db = _session()
    export_zip = tmp_path / "garmin-export.zip"
    _write_export_zip(export_zip, distance=5000.0)

    try:
        import_garmin_summarized_activities(db, client_id="missing-client", source_path=export_zip)
    except GarminActivityImportError as exc:
        assert "Client does not exist" in str(exc)
    else:
        raise AssertionError("Expected GarminActivityImportError")


def test_local_garmin_export_imports_expected_3175_records() -> None:
    if not LOCAL_GARMIN_EXPORT.exists():
        pytest.skip("Local Garmin export ZIP is private raw data and is not committed.")

    db = _session()
    client = _create_placeholder_client(db)

    summary = import_garmin_summarized_activities(
        db,
        client_id=client.id,
        source_path=LOCAL_GARMIN_EXPORT,
    )

    assert summary.records_seen == 3175
    assert summary.records_parsed == 3175
    assert summary.records_invalid == 0
    assert summary.raw_records_created == 3175
    assert summary.activities_inserted == 3175
    assert summary.activities_updated == 0
    assert db.scalar(select(func.count(RawRecord.id))) == 3175
    assert db.scalar(select(func.count(Activity.id))) == 3175
