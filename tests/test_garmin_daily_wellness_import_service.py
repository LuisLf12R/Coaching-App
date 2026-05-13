import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from garmin_api_coach.db import models  # noqa: F401
from garmin_api_coach.db.base import Base
from garmin_api_coach.db.models import Client, Coach, DailyWellnessMetric, DataImport, RawRecord
from garmin_api_coach.imports.garmin_daily_wellness import (
    GarminDailyWellnessImportError,
    import_garmin_daily_wellness,
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


def _write_daily_wellness_zip(export_zip: Path, *, body_battery_most_recent: int) -> None:
    source_file = "DI_CONNECT/DI-Connect-Aggregator/UDSFile_2026-02-02_2026-05-13.json"
    payload = [
        {
            "calendarDate": "2026-05-12",
            "totalSteps": 9533,
            "restingHeartRate": 57,
            "allDayStress": {
                "aggregatorList": [
                    {"type": "TOTAL", "averageStressLevel": 31, "maxStressLevel": 91},
                ]
            },
            "bodyBattery": {
                "chargedValue": 45,
                "drainedValue": 22,
                "bodyBatteryStatList": [
                    {"bodyBatteryStatType": "MOSTRECENT", "statsValue": body_battery_most_recent},
                    {"bodyBatteryStatType": "STARTOFDAY", "statsValue": 28},
                ],
            },
        }
    ]
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps(payload))


def test_import_creates_raw_records_and_daily_wellness_metrics(tmp_path: Path) -> None:
    db = _session()
    client = _create_placeholder_client(db)
    export_zip = tmp_path / "garmin-export.zip"
    _write_daily_wellness_zip(export_zip, body_battery_most_recent=51)

    summary = import_garmin_daily_wellness(db, client_id=client.id, source_path=export_zip)

    assert summary.records_seen == 1
    assert summary.records_parsed == 1
    assert summary.raw_records_created == 1
    assert summary.metrics_inserted == 1
    assert summary.metrics_updated == 0

    data_import = db.get(DataImport, summary.data_import_id)
    raw_record = db.scalar(select(RawRecord))
    metric = db.scalar(select(DailyWellnessMetric))

    assert data_import is not None
    assert data_import.summary["metrics_inserted"] == 1
    assert raw_record is not None
    assert raw_record.source_record_id == "2026-05-12"
    assert metric is not None
    assert metric.client_id == client.id
    assert metric.total_steps == 9533
    assert metric.resting_heart_rate == 57
    assert metric.average_stress_level == 31
    assert metric.body_battery_most_recent == 51


def test_import_upserts_duplicate_daily_wellness_metric(tmp_path: Path) -> None:
    db = _session()
    client = _create_placeholder_client(db)
    export_zip = tmp_path / "garmin-export.zip"

    _write_daily_wellness_zip(export_zip, body_battery_most_recent=51)
    first_summary = import_garmin_daily_wellness(db, client_id=client.id, source_path=export_zip)

    _write_daily_wellness_zip(export_zip, body_battery_most_recent=62)
    second_summary = import_garmin_daily_wellness(db, client_id=client.id, source_path=export_zip)

    metric = db.scalar(select(DailyWellnessMetric))

    assert first_summary.metrics_inserted == 1
    assert second_summary.metrics_inserted == 0
    assert second_summary.metrics_updated == 1
    assert db.scalar(select(func.count(DataImport.id))) == 2
    assert db.scalar(select(func.count(RawRecord.id))) == 2
    assert db.scalar(select(func.count(DailyWellnessMetric.id))) == 1
    assert metric is not None
    assert metric.body_battery_most_recent == 62
    assert metric.data_import_id == second_summary.data_import_id


def test_import_rejects_missing_client(tmp_path: Path) -> None:
    db = _session()
    export_zip = tmp_path / "garmin-export.zip"
    _write_daily_wellness_zip(export_zip, body_battery_most_recent=51)

    with pytest.raises(GarminDailyWellnessImportError, match="Client does not exist"):
        import_garmin_daily_wellness(db, client_id="missing-client", source_path=export_zip)


def test_local_garmin_export_imports_daily_wellness_records() -> None:
    if not LOCAL_GARMIN_EXPORT.exists():
        pytest.skip("Local Garmin export ZIP is private raw data and is not committed.")

    db = _session()
    client = _create_placeholder_client(db)

    summary = import_garmin_daily_wellness(
        db,
        client_id=client.id,
        source_path=LOCAL_GARMIN_EXPORT,
    )

    assert summary.records_seen == 1732
    assert summary.records_parsed == 984
    assert summary.records_invalid == 0
    assert summary.raw_records_created == 984
    assert summary.metrics_inserted == 984
    assert summary.metrics_updated == 0
    assert db.scalar(select(func.count(RawRecord.id))) == 984
    assert db.scalar(select(func.count(DailyWellnessMetric.id))) == 984
