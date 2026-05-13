import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from garmin_api_coach.providers.garmin.summarized_activities import (
    GARMIN_PROVIDER,
    GarminSummarizedActivitiesError,
    load_summarized_activities_from_zip,
)


LOCAL_GARMIN_EXPORT = Path("data/raw/642bffa2-69d5-466c-9599-eb82c5e5124b_1.zip")


def test_load_summarized_activities_from_wrapped_export_zip(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    first_source = "DI_CONNECT/DI-Connect-Fitness/luis_0_summarizedActivities.json"
    second_source = "DI_CONNECT/DI-Connect-Fitness/luis_1001_summarizedActivities.json"

    first_payload = [
        {
            "summarizedActivitiesExport": [
                {
                    "activityId": 123,
                    "activityType": "running",
                    "sportType": "RUNNING",
                    "startTimeGmt": "2026-05-01 12:00:00",
                    "startTimeLocal": "2026-05-01 06:00:00",
                    "duration": 1800.5,
                    "distance": 5000.0,
                    "avgSpeed": 2.77,
                    "avgHr": 145,
                    "maxHr": 178,
                    "calories": 420.0,
                    "steps": 6200,
                    "trainingEffectLabel": "MAINTAINING",
                    "activityTrainingLoad": 72.5,
                    "elapsedDuration": 1810.0,
                    "elevationGain": 45.0,
                    "locationName": "private location",
                },
                {
                    "activityId": "abc",
                    "activityType": "pickleball",
                    "sportType": "RACKET",
                },
            ]
        }
    ]
    second_payload = [
        {
            "activityId": "missing-type",
            "sportType": "RUNNING",
        }
    ]

    with ZipFile(export_zip, "w") as archive:
        archive.writestr(first_source, json.dumps(first_payload))
        archive.writestr(second_source, json.dumps(second_payload))

    summary = load_summarized_activities_from_zip(export_zip)

    assert summary.file_count == 2
    assert summary.records_seen == 3
    assert summary.records_parsed == 2
    assert summary.records_invalid == 1
    assert summary.unknown_activity_types == ("pickleball",)
    assert summary.unknown_sport_types == ("RACKET",)

    first_activity = summary.activities[0]
    assert first_activity.provider == GARMIN_PROVIDER
    assert first_activity.source_file == first_source
    assert first_activity.source_activity_id == "123"
    assert first_activity.activity_type == "running"
    assert first_activity.sport_type == "RUNNING"
    assert first_activity.duration_seconds == 1800.5
    assert first_activity.distance_meters == 5000.0
    assert first_activity.avg_hr == 145
    assert first_activity.provider_metadata == {
        "elapsedDuration": 1810.0,
        "elevationGain": 45.0,
    }
    assert "private location" not in str(first_activity.provider_metadata)


def test_loader_can_use_explicit_activity_file_list(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    selected_source = "custom/path/selected_summarizedActivities.json"
    ignored_source = "custom/path/ignored_summarizedActivities.json"

    with ZipFile(export_zip, "w") as archive:
        archive.writestr(
            selected_source,
            json.dumps(
                {
                    "summarizedActivities": [
                        {
                            "activityId": "selected",
                            "activityType": "cycling",
                            "sportType": "CYCLING",
                        }
                    ]
                }
            ),
        )
        archive.writestr(
            ignored_source,
            json.dumps(
                [
                    {
                        "activityId": "ignored",
                        "activityType": "walking",
                        "sportType": "STEPS",
                    }
                ]
            ),
        )

    summary = load_summarized_activities_from_zip(export_zip, activity_files=[selected_source])

    assert summary.file_count == 1
    assert summary.records_parsed == 1
    assert summary.activities[0].source_activity_id == "selected"


def test_loader_rejects_unsupported_json_structure(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    source_file = "DI_CONNECT/DI-Connect-Fitness/luis_0_summarizedActivities.json"

    with ZipFile(export_zip, "w") as archive:
        archive.writestr(source_file, json.dumps({"unexpected": []}))

    with pytest.raises(GarminSummarizedActivitiesError, match="Unsupported summarized activity JSON structure"):
        load_summarized_activities_from_zip(export_zip)


def test_local_garmin_export_has_expected_summarized_activity_records() -> None:
    if not LOCAL_GARMIN_EXPORT.exists():
        pytest.skip("Local Garmin export ZIP is private raw data and is not committed.")

    summary = load_summarized_activities_from_zip(LOCAL_GARMIN_EXPORT)

    assert summary.file_count == 4
    assert summary.records_seen == 3175
    assert summary.records_parsed == 3175
    assert summary.records_invalid == 0
    assert summary.unknown_activity_types == ()
    assert summary.unknown_sport_types == ()
