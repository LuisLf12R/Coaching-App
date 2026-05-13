import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from garmin_api_coach.providers.garmin.training_readiness import (
    GarminTrainingReadinessError,
    load_training_readiness_from_zip,
)


LOCAL_GARMIN_EXPORT = Path("data/raw/642bffa2-69d5-466c-9599-eb82c5e5124b_1.zip")


def _write_training_readiness_zip(export_zip: Path) -> str:
    source_file = "DI_CONNECT/DI-Connect-Metrics/TrainingReadinessDTO_20260217_20260528_116034249.json"
    payload = [
        {
            "calendarDate": "2026-05-12",
            "timestamp": "2026-05-12T13:16:08.0",
            "timestampLocal": "2026-05-12T07:16:08.0",
            "level": "LOW",
            "score": 36,
            "feedbackShort": "TAKE_IT_EASY",
            "feedbackLong": "LOW_HRV_LOW",
            "sleepScore": 84,
            "sleepScoreFactorPercent": 78,
            "recoveryTime": 1728,
            "recoveryTimeFactorPercent": 53,
            "acwrFactorPercent": 88,
            "stressHistoryFactorPercent": 30,
            "hrvFactorPercent": 39,
            "sleepHistoryFactorPercent": 58,
            "validSleep": True,
            "inputContext": "AFTER_POST_EXERCISE_RESET",
            "hrvWeeklyAverage": 50.0,
            "acuteLoad": 680,
        }
    ]
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps(payload))
    return source_file


def test_training_readiness_parser_reads_records_from_zip(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    source_file = _write_training_readiness_zip(export_zip)

    summary = load_training_readiness_from_zip(export_zip)

    assert summary.file_count == 1
    assert summary.records_seen == 1
    assert summary.records_parsed == 1
    assert summary.records_invalid == 0
    assert summary.levels_seen == ("LOW",)
    record = summary.records[0]
    assert record.source_file == source_file
    assert record.source_record_id == "2026-05-12"
    assert record.score == 36
    assert record.hrv_weekly_average == 50.0
    assert record.raw_payload["feedbackShort"] == "TAKE_IT_EASY"


def test_training_readiness_parser_rejects_unsupported_json_structure(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    source_file = "DI_CONNECT/DI-Connect-Metrics/TrainingReadinessDTO_20260217_20260528_116034249.json"
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps({"not": "a list"}))

    with pytest.raises(GarminTrainingReadinessError, match="Unsupported training readiness JSON structure"):
        load_training_readiness_from_zip(export_zip, source_files=[source_file])


def test_local_garmin_export_training_readiness_records_parse() -> None:
    if not LOCAL_GARMIN_EXPORT.exists():
        pytest.skip("Local Garmin export ZIP is private raw data and is not committed.")

    summary = load_training_readiness_from_zip(LOCAL_GARMIN_EXPORT)

    assert summary.file_count == 4
    assert summary.records_seen == 865
    assert summary.records_parsed == 864
    assert summary.records_invalid == 1
