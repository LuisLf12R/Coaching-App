import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from garmin_api_coach.providers.garmin.daily_wellness import (
    GarminDailyWellnessError,
    load_daily_wellness_from_zip,
)


LOCAL_GARMIN_EXPORT = Path("data/raw/642bffa2-69d5-466c-9599-eb82c5e5124b_1.zip")


def test_load_daily_wellness_from_zip_parses_uds_records(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    source_file = "DI_CONNECT/DI-Connect-Aggregator/UDSFile_2026-02-02_2026-05-13.json"
    payload = [
        {
            "calendarDate": "2026-05-12",
            "totalSteps": 9533,
            "dailyStepGoal": 15000,
            "wellnessDistanceMeters": 8120,
            "restingHeartRate": 57,
            "currentDayRestingHeartRate": 54,
            "minHeartRate": 51,
            "maxHeartRate": 161,
            "moderateIntensityMinutes": 12,
            "vigorousIntensityMinutes": 24,
            "allDayStress": {
                "aggregatorList": [
                    {
                        "type": "TOTAL",
                        "averageStressLevel": 31,
                        "maxStressLevel": 91,
                        "stressDuration": 18000,
                        "restDuration": 42000,
                    }
                ]
            },
            "bodyBattery": {
                "chargedValue": 45,
                "drainedValue": 22,
                "bodyBatteryStatList": [
                    {"bodyBatteryStatType": "HIGHEST", "statsValue": 73},
                    {"bodyBatteryStatType": "LOWEST", "statsValue": 28},
                    {"bodyBatteryStatType": "MOSTRECENT", "statsValue": 51},
                    {"bodyBatteryStatType": "STARTOFDAY", "statsValue": 28},
                ],
            },
            "respiration": {"avgWakingRespirationValue": 14.0},
            "averageSpo2Value": 96.0,
            "lowestSpo2Value": 91,
            "latestSpo2Value": 96,
        },
        {
            "calendarDate": "2006-01-01",
            "totalKilocalories": 524.0,
        },
    ]
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps(payload))

    summary = load_daily_wellness_from_zip(export_zip)

    assert summary.file_count == 1
    assert summary.records_seen == 2
    assert summary.records_parsed == 1
    assert summary.records_invalid == 0

    record = summary.records[0]
    assert record.calendar_date.isoformat() == "2026-05-12"
    assert record.total_steps == 9533
    assert record.resting_heart_rate == 57
    assert record.average_stress_level == 31
    assert record.max_stress_level == 91
    assert record.body_battery_charged == 45
    assert record.body_battery_highest == 73
    assert record.body_battery_most_recent == 51
    assert record.average_waking_respiration == 14.0
    assert record.average_spo2 == 96.0


def test_load_daily_wellness_rejects_unsupported_json_structure(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    source_file = "DI_CONNECT/DI-Connect-Aggregator/UDSFile_2026-02-02_2026-05-13.json"
    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps({"records": []}))

    with pytest.raises(GarminDailyWellnessError, match="Unsupported UDS aggregator JSON structure"):
        load_daily_wellness_from_zip(export_zip)


def test_local_garmin_export_parses_daily_wellness_records() -> None:
    if not LOCAL_GARMIN_EXPORT.exists():
        pytest.skip("Local Garmin export ZIP is private raw data and is not committed.")

    summary = load_daily_wellness_from_zip(LOCAL_GARMIN_EXPORT)

    assert summary.file_count == 19
    assert summary.records_seen == 1732
    assert summary.records_parsed == 984
    assert summary.records_invalid == 0
