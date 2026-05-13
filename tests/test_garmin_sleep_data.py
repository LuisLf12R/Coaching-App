import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from garmin_api_coach.providers.garmin.sleep_data import GarminSleepDataError, load_sleep_data_from_zip


LOCAL_GARMIN_EXPORT = Path("data/raw/642bffa2-69d5-466c-9599-eb82c5e5124b_1.zip")


def _write_sleep_zip(export_zip: Path) -> str:
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
            "unmeasurableSeconds": 0,
            "awakeCount": 0,
            "avgSleepStress": 20.79,
            "restlessMomentCount": 60,
            "averageRespiration": 14.56,
            "lowestRespiration": 10.0,
            "highestRespiration": 22.0,
            "sleepScores": {
                "overallScore": 84,
                "qualityScore": 80,
                "durationScore": 100,
                "recoveryScore": 68,
                "restfulnessScore": 60,
                "feedback": "POSITIVE_LONG_AND_CONTINUOUS",
                "insight": "POSITIVE_STRESSFUL_DAY",
            },
        }
    ]
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps(payload))
    return source_file


def test_sleep_data_parser_reads_records_from_zip(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    source_file = _write_sleep_zip(export_zip)

    summary = load_sleep_data_from_zip(export_zip)

    assert summary.file_count == 1
    assert summary.records_seen == 1
    assert summary.records_parsed == 1
    assert summary.records_invalid == 0
    record = summary.records[0]
    assert record.source_file == source_file
    assert record.source_record_id == "2026-05-12"
    assert record.deep_sleep_seconds == 4680
    assert record.overall_score == 84
    assert record.feedback == "POSITIVE_LONG_AND_CONTINUOUS"
    assert record.raw_payload["sleepScores"]["recoveryScore"] == 68


def test_sleep_data_parser_rejects_unsupported_json_structure(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    source_file = "DI_CONNECT/DI-Connect-Wellness/2026_sleepData.json"
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps({"not": "a list"}))

    with pytest.raises(GarminSleepDataError, match="Unsupported sleep data JSON structure"):
        load_sleep_data_from_zip(export_zip, source_files=[source_file])


def test_local_garmin_export_sleep_records_parse() -> None:
    if not LOCAL_GARMIN_EXPORT.exists():
        pytest.skip("Local Garmin export ZIP is private raw data and is not committed.")

    summary = load_sleep_data_from_zip(LOCAL_GARMIN_EXPORT)

    assert summary.file_count == 10
    assert summary.records_seen == 984
    assert summary.records_parsed == 978
    assert summary.records_invalid == 6
