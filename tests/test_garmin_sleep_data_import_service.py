import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from garmin_api_coach.db import models  # noqa: F401
from garmin_api_coach.db.base import Base
from garmin_api_coach.db.models import Client, Coach, DataImport, RawRecord, SleepMetric
from garmin_api_coach.imports.garmin_sleep_data import GarminSleepDataImportError, import_garmin_sleep_data


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


def _write_sleep_zip(export_zip: Path, *, score: int) -> None:
    source_file = "DI_CONNECT/DI-Connect-Wellness/2026-02-03_2026-05-14_116034249_sleepData.json"
    payload = [
        {
            "calendarDate": "2026-05-12",
            "sleepStartTimestampGMT": "2026-05-12T02:34:00.0",
            "sleepEndTimestampGMT": "2026-05-12T10:11:00.0",
            "deepSleepSeconds": 4680,
            "lightSleepSeconds": 16560,
            "remSleepSeconds": 5700,
            "awakeSleepSeconds": 480,
            "avgSleepStress": 20.79,
            "sleepScores": {
                "overallScore": score,
                "qualityScore": 80,
                "durationScore": 100,
                "recoveryScore": 68,
                "restfulnessScore": 60,
            },
        }
    ]
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps(payload))


def test_import_creates_raw_records_and_sleep_metrics(tmp_path: Path) -> None:
    db = _session()
    client = _create_placeholder_client(db)
    export_zip = tmp_path / "garmin-export.zip"
    _write_sleep_zip(export_zip, score=84)

    summary = import_garmin_sleep_data(db, client_id=client.id, source_path=export_zip)

    assert summary.records_seen == 1
    assert summary.records_parsed == 1
    assert summary.raw_records_created == 1
    assert summary.metrics_inserted == 1
    assert summary.metrics_updated == 0

    data_import = db.get(DataImport, summary.data_import_id)
    raw_record = db.scalar(select(RawRecord))
    metric = db.scalar(select(SleepMetric))

    assert data_import is not None
    assert data_import.summary["metrics_inserted"] == 1
    assert raw_record is not None
    assert raw_record.source_record_id == "2026-05-12"
    assert metric is not None
    assert metric.client_id == client.id
    assert metric.overall_score == 84
    assert metric.deep_sleep_seconds == 4680
    assert metric.recovery_score == 68


def test_import_upserts_duplicate_sleep_metric(tmp_path: Path) -> None:
    db = _session()
    client = _create_placeholder_client(db)
    export_zip = tmp_path / "garmin-export.zip"

    _write_sleep_zip(export_zip, score=84)
    first_summary = import_garmin_sleep_data(db, client_id=client.id, source_path=export_zip)

    _write_sleep_zip(export_zip, score=90)
    second_summary = import_garmin_sleep_data(db, client_id=client.id, source_path=export_zip)

    metric = db.scalar(select(SleepMetric))

    assert first_summary.metrics_inserted == 1
    assert second_summary.metrics_inserted == 0
    assert second_summary.metrics_updated == 1
    assert db.scalar(select(func.count(DataImport.id))) == 2
    assert db.scalar(select(func.count(RawRecord.id))) == 2
    assert db.scalar(select(func.count(SleepMetric.id))) == 1
    assert metric is not None
    assert metric.overall_score == 90
    assert metric.data_import_id == second_summary.data_import_id


def test_import_rejects_missing_client(tmp_path: Path) -> None:
    db = _session()
    export_zip = tmp_path / "garmin-export.zip"
    _write_sleep_zip(export_zip, score=84)

    with pytest.raises(GarminSleepDataImportError, match="Client does not exist"):
        import_garmin_sleep_data(db, client_id="missing-client", source_path=export_zip)


def test_local_garmin_export_imports_sleep_records() -> None:
    if not LOCAL_GARMIN_EXPORT.exists():
        pytest.skip("Local Garmin export ZIP is private raw data and is not committed.")

    db = _session()
    client = _create_placeholder_client(db)

    summary = import_garmin_sleep_data(
        db,
        client_id=client.id,
        source_path=LOCAL_GARMIN_EXPORT,
    )

    assert summary.records_seen == 984
    assert summary.records_parsed == 978
    assert summary.records_invalid == 6
    assert summary.raw_records_created == 978
    assert summary.metrics_inserted == 978
    assert summary.metrics_updated == 0
    assert db.scalar(select(func.count(RawRecord.id))) == 978
    assert db.scalar(select(func.count(SleepMetric.id))) == 978
