import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from garmin_api_coach.providers.garmin.health_status import GarminHealthStatusError, load_health_status_from_zip


LOCAL_GARMIN_EXPORT = Path("data/raw/642bffa2-69d5-466c-9599-eb82c5e5124b_1.zip")


def _write_health_status_zip(export_zip: Path) -> str:
    source_file = "DI_CONNECT/DI-Connect-Wellness/2026-02-01_2026-05-12_116034249_healthStatusData.json"
    payload = [
        {
            "calendarDate": "2026-05-12",
            "createTimestampUTC": "2026-05-12T10:45:00.0",
            "updateTimestampUTC": "2026-05-12T11:15:00.0",
            "outliersCount": 1,
            "metrics": [
                {
                    "type": "HR",
                    "value": 58.0,
                    "baselineUpperLimit": 64.0,
                    "baselineLowerLimit": 48.0,
                    "status": "NORMAL",
                    "percentage": 0.0,
                    "feedbackKey": "HEART_RATE_NORMAL",
                },
                {
                    "type": "HRV",
                    "value": 62.0,
                    "baselineUpperLimit": 72.0,
                    "baselineLowerLimit": 45.0,
                    "status": "NORMAL",
                    "percentage": 0.0,
                    "feedbackKey": "HRV_NORMAL",
                },
                {
                    "type": "RESPIRATION",
                    "value": 14.2,
                    "status": "NORMAL",
                },
            ],
        }
    ]
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps(payload))
    return source_file


def test_health_status_parser_reads_records_from_zip(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    source_file = _write_health_status_zip(export_zip)

    summary = load_health_status_from_zip(export_zip)

    assert summary.file_count == 1
    assert summary.records_seen == 1
    assert summary.records_parsed == 1
    assert summary.records_invalid == 0
    assert summary.metric_types_seen == ("HR", "HRV", "RESPIRATION")
    record = summary.records[0]
    assert record.source_file == source_file
    assert record.source_record_id == "2026-05-12"
    assert record.heart_rate_value == 58.0
    assert record.heart_rate_baseline_lower == 48.0
    assert record.hrv_value == 62.0
    assert record.respiration_value == 14.2
    assert record.raw_payload["outliersCount"] == 1


def test_health_status_parser_rejects_unsupported_json_structure(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    source_file = "DI_CONNECT/DI-Connect-Wellness/2026_healthStatusData.json"
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps({"not": "a list"}))

    with pytest.raises(GarminHealthStatusError, match="Unsupported health-status JSON structure"):
        load_health_status_from_zip(export_zip, source_files=[source_file])


def test_local_garmin_export_health_status_records_parse() -> None:
    if not LOCAL_GARMIN_EXPORT.exists():
        pytest.skip("Local Garmin export ZIP is private raw data and is not committed.")

    summary = load_health_status_from_zip(LOCAL_GARMIN_EXPORT)

    assert summary.file_count == 3
    assert summary.records_seen == 235
    assert summary.records_parsed == 235
    assert summary.records_invalid == 0
    assert summary.metric_types_seen == ("HR", "HRV", "RESPIRATION", "SKIN_TEMP_C", "SPO2")
