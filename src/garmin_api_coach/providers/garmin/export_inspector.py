from dataclasses import dataclass
from pathlib import Path
from typing import Union
from zipfile import BadZipFile, ZipFile


DI_CONNECT_PREFIX = "DI_CONNECT/"
SUMMARIZED_ACTIVITIES_SUFFIX = "_summarizedActivities.json"
TRAINING_READINESS_PREFIX = "DI_CONNECT/DI-Connect-Metrics/TrainingReadinessDTO_"
SLEEP_DATA_SUFFIX = "_sleepData.json"
HEALTH_STATUS_DATA_SUFFIX = "_healthStatusData.json"
ACUTE_TRAINING_LOAD_PREFIX = "DI_CONNECT/DI-Connect-Metrics/MetricsAcuteTrainingLoad_"
UDS_AGGREGATOR_PREFIX = "DI_CONNECT/DI-Connect-Aggregator/UDSFile_"


class GarminExportInspectionError(ValueError):
    """Raised when a Garmin export file cannot be inspected."""


@dataclass(frozen=True)
class GarminExportInspection:
    source_path: Path
    total_entries: int
    json_files: tuple[str, ...]
    nested_zip_files: tuple[str, ...]
    png_files: tuple[str, ...]
    top_level_folders: tuple[str, ...]
    di_connect_folders: tuple[str, ...]
    summarized_activity_files: tuple[str, ...]
    training_readiness_files: tuple[str, ...]
    sleep_data_files: tuple[str, ...]
    health_status_files: tuple[str, ...]
    acute_training_load_files: tuple[str, ...]
    uds_aggregator_files: tuple[str, ...]

    @property
    def has_di_connect(self) -> bool:
        return any(folder == "DI_CONNECT" for folder in self.top_level_folders)

    @property
    def summarized_activity_file_count(self) -> int:
        return len(self.summarized_activity_files)

    @property
    def training_readiness_file_count(self) -> int:
        return len(self.training_readiness_files)

    @property
    def sleep_data_file_count(self) -> int:
        return len(self.sleep_data_files)

    @property
    def health_status_file_count(self) -> int:
        return len(self.health_status_files)

    @property
    def acute_training_load_file_count(self) -> int:
        return len(self.acute_training_load_files)

    @property
    def uds_aggregator_file_count(self) -> int:
        return len(self.uds_aggregator_files)

    def to_summary(self) -> dict[str, object]:
        return {
            "source_path": str(self.source_path),
            "total_entries": self.total_entries,
            "json_file_count": len(self.json_files),
            "nested_zip_file_count": len(self.nested_zip_files),
            "png_file_count": len(self.png_files),
            "top_level_folders": list(self.top_level_folders),
            "di_connect_folders": list(self.di_connect_folders),
            "summarized_activity_files": list(self.summarized_activity_files),
            "summarized_activity_file_count": self.summarized_activity_file_count,
            "training_readiness_files": list(self.training_readiness_files),
            "training_readiness_file_count": self.training_readiness_file_count,
            "sleep_data_files": list(self.sleep_data_files),
            "sleep_data_file_count": self.sleep_data_file_count,
            "health_status_files": list(self.health_status_files),
            "health_status_file_count": self.health_status_file_count,
            "acute_training_load_files": list(self.acute_training_load_files),
            "acute_training_load_file_count": self.acute_training_load_file_count,
            "uds_aggregator_files": list(self.uds_aggregator_files),
            "uds_aggregator_file_count": self.uds_aggregator_file_count,
        }


def inspect_garmin_export_zip(source_path: Union[Path, str]) -> GarminExportInspection:
    export_path = Path(source_path)
    if not export_path.exists():
        raise GarminExportInspectionError(f"Garmin export ZIP does not exist: {export_path}")
    if not export_path.is_file():
        raise GarminExportInspectionError(f"Garmin export path is not a file: {export_path}")

    try:
        with ZipFile(export_path) as archive:
            entry_names = tuple(info.filename for info in archive.infolist() if not info.is_dir())
    except BadZipFile as exc:
        raise GarminExportInspectionError(f"Invalid Garmin export ZIP: {export_path}") from exc

    json_files = tuple(sorted(name for name in entry_names if name.lower().endswith(".json")))
    nested_zip_files = tuple(sorted(name for name in entry_names if name.lower().endswith(".zip")))
    png_files = tuple(sorted(name for name in entry_names if name.lower().endswith(".png")))
    top_level_folders = tuple(sorted({name.split("/", 1)[0] for name in entry_names if "/" in name}))
    di_connect_folders = tuple(
        sorted(
            {
                name.split("/", 2)[1]
                for name in entry_names
                if name.startswith(DI_CONNECT_PREFIX) and len(name.split("/", 2)) >= 3
            }
        )
    )
    summarized_activity_files = tuple(
        sorted(
            name
            for name in json_files
            if name.startswith("DI_CONNECT/DI-Connect-Fitness/")
            and name.endswith(SUMMARIZED_ACTIVITIES_SUFFIX)
        )
    )
    training_readiness_files = tuple(
        sorted(
            name
            for name in json_files
            if name.startswith(TRAINING_READINESS_PREFIX)
        )
    )
    sleep_data_files = tuple(
        sorted(
            name
            for name in json_files
            if name.startswith("DI_CONNECT/DI-Connect-Wellness/")
            and name.endswith(SLEEP_DATA_SUFFIX)
        )
    )
    health_status_files = tuple(
        sorted(
            name
            for name in json_files
            if name.startswith("DI_CONNECT/DI-Connect-Wellness/")
            and name.endswith(HEALTH_STATUS_DATA_SUFFIX)
        )
    )
    acute_training_load_files = tuple(
        sorted(
            name
            for name in json_files
            if name.startswith(ACUTE_TRAINING_LOAD_PREFIX)
        )
    )
    uds_aggregator_files = tuple(
        sorted(
            name
            for name in json_files
            if name.startswith(UDS_AGGREGATOR_PREFIX)
        )
    )

    return GarminExportInspection(
        source_path=export_path,
        total_entries=len(entry_names),
        json_files=json_files,
        nested_zip_files=nested_zip_files,
        png_files=png_files,
        top_level_folders=top_level_folders,
        di_connect_folders=di_connect_folders,
        summarized_activity_files=summarized_activity_files,
        training_readiness_files=training_readiness_files,
        sleep_data_files=sleep_data_files,
        health_status_files=health_status_files,
        acute_training_load_files=acute_training_load_files,
        uds_aggregator_files=uds_aggregator_files,
    )
