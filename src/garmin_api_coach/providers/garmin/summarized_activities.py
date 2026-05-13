import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional, Union
from zipfile import BadZipFile, ZipFile

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from garmin_api_coach.providers.garmin.export_inspector import inspect_garmin_export_zip


PARSER_VERSION = "garmin_summarized_activities_v1"
GARMIN_PROVIDER = "garmin"

KNOWN_ACTIVITY_TYPES = frozenset(
    {
        "basketball",
        "boxing",
        "cycling",
        "hiit",
        "indoor_cardio",
        "indoor_cycling",
        "indoor_rowing",
        "lap_swimming",
        "mobility",
        "multi_sport",
        "other",
        "paddelball",
        "running",
        "stair_climbing",
        "strength_training",
        "swimming",
        "treadmill_running",
        "walking",
    }
)

KNOWN_SPORT_TYPES = frozenset(
    {
        "BASKETBALL",
        "CYCLING",
        "FITNESS_EQUIPMENT",
        "GENERIC",
        "HIIT",
        "INVALID",
        "MULTISPORT",
        "ROWING",
        "RUNNING",
        "STEPS",
        "SWIMMING",
        "TRAINING",
    }
)


class GarminSummarizedActivitiesError(ValueError):
    """Raised when summarized Garmin activity records cannot be parsed."""


class GarminSummarizedActivityRecord(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    activity_id: str = Field(alias="activityId")
    activity_type: str = Field(alias="activityType")
    sport_type: Optional[str] = Field(default=None, alias="sportType")
    start_time_gmt: Optional[datetime] = Field(default=None, alias="startTimeGmt")
    start_time_local: Optional[datetime] = Field(default=None, alias="startTimeLocal")
    duration_seconds: Optional[float] = Field(default=None, alias="duration")
    distance_meters: Optional[float] = Field(default=None, alias="distance")
    avg_speed_meters_per_second: Optional[float] = Field(default=None, alias="avgSpeed")
    avg_hr: Optional[int] = Field(default=None, alias="avgHr")
    max_hr: Optional[int] = Field(default=None, alias="maxHr")
    calories: Optional[float] = None
    steps: Optional[int] = None
    training_effect_label: Optional[str] = Field(default=None, alias="trainingEffectLabel")
    activity_training_load: Optional[float] = Field(default=None, alias="activityTrainingLoad")

    @field_validator("activity_id", mode="before")
    @classmethod
    def coerce_activity_id(cls, value: object) -> str:
        if value is None or value == "":
            raise ValueError("activityId is required")
        return str(value)

    @field_validator("activity_type")
    @classmethod
    def activity_type_is_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("activityType is required")
        return value

    @field_validator("sport_type")
    @classmethod
    def normalize_blank_sport_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


@dataclass(frozen=True)
class ParsedGarminSummarizedActivity:
    provider: str
    parser_version: str
    source_file: str
    source_activity_id: str
    activity_type: str
    sport_type: Optional[str]
    start_time_gmt: Optional[datetime]
    start_time_local: Optional[datetime]
    duration_seconds: Optional[float]
    distance_meters: Optional[float]
    avg_speed_meters_per_second: Optional[float]
    avg_hr: Optional[int]
    max_hr: Optional[int]
    calories: Optional[float]
    steps: Optional[int]
    training_effect_label: Optional[str]
    activity_training_load: Optional[float]
    provider_metadata: dict[str, Any]
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class GarminSummarizedActivityValidationIssue:
    source_file: str
    record_index: int
    message: str


@dataclass(frozen=True)
class GarminSummarizedActivityFileSummary:
    source_file: str
    records_seen: int
    records_parsed: int
    records_invalid: int


@dataclass(frozen=True)
class GarminSummarizedActivitiesImportSummary:
    source_path: Path
    parser_version: str
    activity_files: tuple[str, ...]
    file_summaries: tuple[GarminSummarizedActivityFileSummary, ...]
    activities: tuple[ParsedGarminSummarizedActivity, ...]
    validation_issues: tuple[GarminSummarizedActivityValidationIssue, ...]
    activity_types_seen: tuple[str, ...]
    sport_types_seen: tuple[str, ...]
    unknown_activity_types: tuple[str, ...]
    unknown_sport_types: tuple[str, ...]

    @property
    def file_count(self) -> int:
        return len(self.activity_files)

    @property
    def records_seen(self) -> int:
        return sum(summary.records_seen for summary in self.file_summaries)

    @property
    def records_parsed(self) -> int:
        return len(self.activities)

    @property
    def records_invalid(self) -> int:
        return len(self.validation_issues)

    def to_summary(self) -> dict[str, object]:
        return {
            "source_path": str(self.source_path),
            "parser_version": self.parser_version,
            "file_count": self.file_count,
            "records_seen": self.records_seen,
            "records_parsed": self.records_parsed,
            "records_invalid": self.records_invalid,
            "activity_files": list(self.activity_files),
            "activity_types_seen": list(self.activity_types_seen),
            "sport_types_seen": list(self.sport_types_seen),
            "unknown_activity_types": list(self.unknown_activity_types),
            "unknown_sport_types": list(self.unknown_sport_types),
        }


def load_summarized_activities_from_zip(
    source_path: Union[Path, str],
    activity_files: Optional[Iterable[str]] = None,
) -> GarminSummarizedActivitiesImportSummary:
    export_path = Path(source_path)
    if activity_files is None:
        inspection = inspect_garmin_export_zip(export_path)
        selected_activity_files = inspection.summarized_activity_files
    else:
        selected_activity_files = tuple(sorted(activity_files))

    activities: list[ParsedGarminSummarizedActivity] = []
    validation_issues: list[GarminSummarizedActivityValidationIssue] = []
    file_summaries: list[GarminSummarizedActivityFileSummary] = []
    activity_types_seen: set[str] = set()
    sport_types_seen: set[str] = set()

    try:
        with ZipFile(export_path) as archive:
            archive_names = set(archive.namelist())
            for source_file in selected_activity_files:
                if source_file not in archive_names:
                    raise GarminSummarizedActivitiesError(
                        f"Summarized activity file is missing from ZIP: {source_file}"
                    )

                payload = _read_json_from_zip(archive, source_file)
                candidate_records = _extract_activity_records(payload, source_file)
                parsed_count_before = len(activities)
                invalid_count_before = len(validation_issues)

                for record_index, raw_record in enumerate(candidate_records):
                    parsed_record = _parse_record(raw_record, source_file, record_index)
                    if isinstance(parsed_record, GarminSummarizedActivityValidationIssue):
                        validation_issues.append(parsed_record)
                        continue

                    activities.append(parsed_record)
                    activity_types_seen.add(parsed_record.activity_type)
                    if parsed_record.sport_type is not None:
                        sport_types_seen.add(parsed_record.sport_type)

                file_summaries.append(
                    GarminSummarizedActivityFileSummary(
                        source_file=source_file,
                        records_seen=len(candidate_records),
                        records_parsed=len(activities) - parsed_count_before,
                        records_invalid=len(validation_issues) - invalid_count_before,
                    )
                )
    except BadZipFile as exc:
        raise GarminSummarizedActivitiesError(f"Invalid Garmin export ZIP: {export_path}") from exc

    return GarminSummarizedActivitiesImportSummary(
        source_path=export_path,
        parser_version=PARSER_VERSION,
        activity_files=selected_activity_files,
        file_summaries=tuple(file_summaries),
        activities=tuple(activities),
        validation_issues=tuple(validation_issues),
        activity_types_seen=tuple(sorted(activity_types_seen)),
        sport_types_seen=tuple(sorted(sport_types_seen)),
        unknown_activity_types=tuple(sorted(activity_types_seen - KNOWN_ACTIVITY_TYPES)),
        unknown_sport_types=tuple(sorted(sport_types_seen - KNOWN_SPORT_TYPES)),
    )


def _read_json_from_zip(archive: ZipFile, source_file: str) -> object:
    try:
        with archive.open(source_file) as file_handle:
            return json.load(file_handle)
    except json.JSONDecodeError as exc:
        raise GarminSummarizedActivitiesError(f"Invalid JSON in summarized activity file: {source_file}") from exc


def _extract_activity_records(payload: object, source_file: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        if _is_wrapped_export(payload):
            records: list[dict[str, Any]] = []
            for wrapper in payload:
                records.extend(_extract_activity_records(wrapper["summarizedActivitiesExport"], source_file))
            return records

        if all(isinstance(item, dict) for item in payload):
            return payload

    if isinstance(payload, dict):
        if "summarizedActivitiesExport" in payload:
            return _extract_activity_records(payload["summarizedActivitiesExport"], source_file)
        if "summarizedActivities" in payload:
            return _extract_activity_records(payload["summarizedActivities"], source_file)

    raise GarminSummarizedActivitiesError(
        f"Unsupported summarized activity JSON structure in file: {source_file}"
    )


def _is_wrapped_export(payload: list[object]) -> bool:
    return bool(payload) and all(
        isinstance(item, dict) and set(item.keys()) == {"summarizedActivitiesExport"} for item in payload
    )


def _parse_record(
    raw_record: dict[str, Any],
    source_file: str,
    record_index: int,
) -> Union[ParsedGarminSummarizedActivity, GarminSummarizedActivityValidationIssue]:
    try:
        record = GarminSummarizedActivityRecord.model_validate(raw_record)
    except ValidationError as exc:
        return GarminSummarizedActivityValidationIssue(
            source_file=source_file,
            record_index=record_index,
            message=str(exc.errors(include_url=False)),
        )

    return ParsedGarminSummarizedActivity(
        provider=GARMIN_PROVIDER,
        parser_version=PARSER_VERSION,
        source_file=source_file,
        source_activity_id=record.activity_id,
        activity_type=record.activity_type,
        sport_type=record.sport_type,
        start_time_gmt=record.start_time_gmt,
        start_time_local=record.start_time_local,
        duration_seconds=record.duration_seconds,
        distance_meters=record.distance_meters,
        avg_speed_meters_per_second=record.avg_speed_meters_per_second,
        avg_hr=record.avg_hr,
        max_hr=record.max_hr,
        calories=record.calories,
        steps=record.steps,
        training_effect_label=record.training_effect_label,
        activity_training_load=record.activity_training_load,
        provider_metadata=_provider_metadata_from_record(record),
        raw_payload=raw_record,
    )


def _provider_metadata_from_record(record: GarminSummarizedActivityRecord) -> dict[str, Any]:
    metadata_keys = {
        "aerobicTrainingEffect",
        "anaerobicTrainingEffect",
        "avgPower",
        "elapsedDuration",
        "elevationGain",
        "elevationLoss",
        "lapCount",
        "movingDuration",
        "vO2MaxValue",
        "workoutFeel",
        "workoutRpe",
    }
    extras = record.model_extra or {}
    return {key: extras[key] for key in sorted(metadata_keys) if key in extras}
