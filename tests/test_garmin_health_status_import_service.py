import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from garmin_api_coach.db import models  # noqa: F401
from garmin_api_coach.db.base import Base
from garmin_api_coach.db.models import Client, Coach, DataImport, HealthStatusMetric, RawRecord
from garmin_api_coach.imports.garmin_health_status import GarminHealthStatusImportError, import_garmin_health_status


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


def _write_health_status_zip(export_zip: Path, *, hrv_value: float) -> None:
    source_file = "DI_CONNECT/DI-Connect-Wellness/2026-02-01_2026-05-12_116034249_healthStatusData.json"
    payload = [
        {
            "calendarDate": "2026-05-12",
            "createTimestampUTC": "2026-05-12T10:45:00.0",
            "updateTimestampUTC": "2026-05-12T11:15:00.0",
            "outliersCount": 1,
            "metrics": [
                {"type": "HR", "value": 58.0, "status": "NORMAL"},
                {"type": "HRV", "value": hrv_value, "status": "NORMAL"},
                {"type": "RESPIRATION", "value": 14.2, "status": "NORMAL"},
            ],
        }
    ]
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps(payload))


def test_import_creates_raw_records_and_health_status_metrics(tmp_path: Path) -> None:
    db = _session()
    client = _create_placeholder_client(db)
    export_zip = tmp_path / "garmin-export.zip"
    _write_health_status_zip(export_zip, hrv_value=62.0)

    summary = import_garmin_health_status(db, client_id=client.id, source_path=export_zip)

    assert summary.records_seen == 1
    assert summary.records_parsed == 1
    assert summary.raw_records_created == 1
    assert summary.metrics_inserted == 1
    assert summary.metrics_updated == 0

    data_import = db.get(DataImport, summary.data_import_id)
    raw_record = db.scalar(select(RawRecord))
    metric = db.scalar(select(HealthStatusMetric))

    assert data_import is not None
    assert data_import.summary["metrics_inserted"] == 1
    assert data_import.summary["metric_types_seen"] == ["HR", "HRV", "RESPIRATION"]
    assert raw_record is not None
    assert raw_record.source_record_id == "2026-05-12"
    assert metric is not None
    assert metric.client_id == client.id
    assert metric.heart_rate_value == 58.0
    assert metric.hrv_value == 62.0
    assert metric.respiration_value == 14.2


def test_import_upserts_duplicate_health_status_metric(tmp_path: Path) -> None:
    db = _session()
    client = _create_placeholder_client(db)
    export_zip = tmp_path / "garmin-export.zip"

    _write_health_status_zip(export_zip, hrv_value=62.0)
    first_summary = import_garmin_health_status(db, client_id=client.id, source_path=export_zip)

    _write_health_status_zip(export_zip, hrv_value=68.0)
    second_summary = import_garmin_health_status(db, client_id=client.id, source_path=export_zip)

    metric = db.scalar(select(HealthStatusMetric))

    assert first_summary.metrics_inserted == 1
    assert second_summary.metrics_inserted == 0
    assert second_summary.metrics_updated == 1
    assert db.scalar(select(func.count(DataImport.id))) == 2
    assert db.scalar(select(func.count(RawRecord.id))) == 2
    assert db.scalar(select(func.count(HealthStatusMetric.id))) == 1
    assert metric is not None
    assert metric.hrv_value == 68.0
    assert metric.data_import_id == second_summary.data_import_id


def test_import_rejects_missing_client(tmp_path: Path) -> None:
    db = _session()
    export_zip = tmp_path / "garmin-export.zip"
    _write_health_status_zip(export_zip, hrv_value=62.0)

    with pytest.raises(GarminHealthStatusImportError, match="Client does not exist"):
        import_garmin_health_status(db, client_id="missing-client", source_path=export_zip)


def test_local_garmin_export_imports_health_status_records() -> None:
    if not LOCAL_GARMIN_EXPORT.exists():
        pytest.skip("Local Garmin export ZIP is private raw data and is not committed.")

    db = _session()
    client = _create_placeholder_client(db)

    summary = import_garmin_health_status(
        db,
        client_id=client.id,
        source_path=LOCAL_GARMIN_EXPORT,
    )

    assert summary.records_seen == 235
    assert summary.records_parsed == 235
    assert summary.records_invalid == 0
    assert summary.raw_records_created == 235
    assert summary.metrics_inserted == 235
    assert summary.metrics_updated == 0
    assert db.scalar(select(func.count(RawRecord.id))) == 235
    assert db.scalar(select(func.count(HealthStatusMetric.id))) == 235
