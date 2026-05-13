import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from garmin_api_coach.providers.garmin.acute_training_load import (
    GarminAcuteTrainingLoadError,
    load_acute_training_load_from_zip,
)


LOCAL_GARMIN_EXPORT = Path("data/raw/642bffa2-69d5-466c-9599-eb82c5e5124b_1.zip")


def _write_acute_training_load_zip(export_zip: Path) -> str:
    source_file = "DI_CONNECT/DI-Connect-Metrics/MetricsAcuteTrainingLoad_20260217_20260528_116034249.json"
    payload = [
        {
            "calendarDate": 1771286400000,
            "timestamp": 1771241954000,
            "acwrPercent": 83,
            "acwrStatus": "OPTIMAL",
            "acwrStatusFeedback": "FEEDBACK_2",
            "dailyTrainingLoadAcute": 908,
            "dailyTrainingLoadChronic": 1089,
            "dailyAcuteChronicWorkloadRatio": 0.8,
        }
    ]
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps(payload))
    return source_file


def test_acute_training_load_parser_reads_records_from_zip(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    source_file = _write_acute_training_load_zip(export_zip)

    summary = load_acute_training_load_from_zip(export_zip)

    assert summary.file_count == 1
    assert summary.records_seen == 1
    assert summary.records_parsed == 1
    assert summary.records_invalid == 0
    assert summary.statuses_seen == ("OPTIMAL",)
    record = summary.records[0]
    assert record.source_file == source_file
    assert record.source_record_id == "2026-02-17"
    assert record.acwr_percent == 83
    assert record.daily_training_load_acute == 908
    assert record.daily_acute_chronic_workload_ratio == 0.8


def test_acute_training_load_parser_rejects_unsupported_json_structure(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    source_file = "DI_CONNECT/DI-Connect-Metrics/MetricsAcuteTrainingLoad_20260217_20260528_116034249.json"
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps({"not": "a list"}))

    with pytest.raises(GarminAcuteTrainingLoadError, match="Unsupported acute training load JSON structure"):
        load_acute_training_load_from_zip(export_zip, source_files=[source_file])


def test_local_garmin_export_acute_training_load_records_parse() -> None:
    if not LOCAL_GARMIN_EXPORT.exists():
        pytest.skip("Local Garmin export ZIP is private raw data and is not committed.")

    summary = load_acute_training_load_from_zip(LOCAL_GARMIN_EXPORT)

    assert summary.file_count == 10
    assert summary.records_seen == 2911
    assert summary.records_parsed == 2911
    assert summary.records_invalid == 0
