from pathlib import Path
from zipfile import ZipFile

import pytest

from garmin_api_coach.providers.garmin.export_inspector import (
    GarminExportInspectionError,
    inspect_garmin_export_zip,
)


LOCAL_GARMIN_EXPORT = Path("data/raw/642bffa2-69d5-466c-9599-eb82c5e5124b_1.zip")


def test_inspector_finds_garmin_export_structure(tmp_path: Path) -> None:
    export_zip = tmp_path / "garmin-export.zip"
    with ZipFile(export_zip, "w") as archive:
        archive.writestr("customer_data/customer.json", "{}")
        archive.writestr("DI_CONNECT/DI-Connect-Fitness/luis_0_summarizedActivities.json", "[]")
        archive.writestr("DI_CONNECT/DI-Connect-Fitness/luis_1001_summarizedActivities.json", "[]")
        archive.writestr("DI_CONNECT/DI-Connect-Metrics/TrainingReadinessDTO_20260217_20260528_116034249.json", "[]")
        archive.writestr("DI_CONNECT/DI-Connect-Wellness/2026_sleepData.json", "[]")
        archive.writestr("DI_CONNECT/DI-Connect-Wellness/2026_healthStatusData.json", "[]")
        archive.writestr("DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_0-_Part1.zip", b"")
        archive.writestr("DI_CONNECT/DI-Connect-Device/device.png", b"")

    inspection = inspect_garmin_export_zip(export_zip)

    assert inspection.total_entries == 8
    assert inspection.has_di_connect is True
    assert inspection.summarized_activity_file_count == 2
    assert inspection.training_readiness_file_count == 1
    assert inspection.sleep_data_file_count == 1
    assert inspection.summarized_activity_files == (
        "DI_CONNECT/DI-Connect-Fitness/luis_0_summarizedActivities.json",
        "DI_CONNECT/DI-Connect-Fitness/luis_1001_summarizedActivities.json",
    )
    assert "DI-Connect-Fitness" in inspection.di_connect_folders
    assert inspection.to_summary()["nested_zip_file_count"] == 1


def test_inspector_rejects_missing_file() -> None:
    with pytest.raises(GarminExportInspectionError, match="does not exist"):
        inspect_garmin_export_zip("missing-export.zip")


def test_inspector_rejects_invalid_zip(tmp_path: Path) -> None:
    invalid_zip = tmp_path / "not-a-zip.zip"
    invalid_zip.write_text("not a zip")

    with pytest.raises(GarminExportInspectionError, match="Invalid Garmin export ZIP"):
        inspect_garmin_export_zip(invalid_zip)


def test_local_garmin_export_has_expected_summarized_activity_files() -> None:
    if not LOCAL_GARMIN_EXPORT.exists():
        pytest.skip("Local Garmin export ZIP is private raw data and is not committed.")

    inspection = inspect_garmin_export_zip(LOCAL_GARMIN_EXPORT)

    assert inspection.has_di_connect is True
    assert inspection.summarized_activity_file_count == 4
    assert inspection.to_summary()["json_file_count"] == 151
    assert inspection.to_summary()["nested_zip_file_count"] == 7
    assert inspection.training_readiness_file_count == 4
    assert inspection.sleep_data_file_count == 10
