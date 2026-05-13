import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional, Union
from zipfile import BadZipFile, ZipFile

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from garmin_api_coach.providers.garmin.export_inspector import inspect_garmin_export_zip
from garmin_api_coach.providers.garmin.summarized_activities import GARMIN_PROVIDER


PARSER_VERSION = "garmin_training_readiness_v1"


class GarminTrainingReadinessError(ValueError):
    """Raised when Garmin training readiness records cannot be parsed."""


class GarminTrainingReadinessRecord(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    calendar_date: date = Field(alias="calendarDate")
    timestamp: Optional[datetime] = None
    timestamp_local: Optional[datetime] = Field(default=None, alias="timestampLocal")
    level: str
    score: int
    feedback_short: Optional[str] = Field(default=None, alias="feedbackShort")
    feedback_long: Optional[str] = Field(default=None, alias="feedbackLong")
    sleep_score: Optional[int] = Field(default=None, alias="sleepScore")
    sleep_score_factor_percent: Optional[int] = Field(default=None, alias="sleepScoreFactorPercent")
    recovery_time: Optional[int] = Field(default=None, alias="recoveryTime")
    recovery_time_factor_percent: Optional[int] = Field(default=None, alias="recoveryTimeFactorPercent")
    acwr_factor_percent: Optional[int] = Field(default=None, alias="acwrFactorPercent")
    stress_history_factor_percent: Optional[int] = Field(default=None, alias="stressHistoryFactorPercent")
    hrv_factor_percent: Optional[int] = Field(default=None, alias="hrvFactorPercent")
    sleep_history_factor_percent: Optional[int] = Field(default=None, alias="sleepHistoryFactorPercent")
    valid_sleep: Optional[bool] = Field(default=None, alias="validSleep")
    input_context: Optional[str] = Field(default=None, alias="inputContext")
    hrv_weekly_average: Optional[float] = Field(default=None, alias="hrvWeeklyAverage")
    acute_load: Optional[float] = Field(default=None, alias="acuteLoad")

    @field_validator("level")
    @classmethod
    def level_is_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("level is required")
        return value


@dataclass(frozen=True)
class ParsedGarminTrainingReadiness:
    provider: str
    parser_version: str
    source_file: str
    source_record_id: str
    calendar_date: date
    timestamp: Optional[datetime]
    timestamp_local: Optional[datetime]
    level: str
    score: int
    feedback_short: Optional[str]
    feedback_long: Optional[str]
    sleep_score: Optional[int]
    sleep_score_factor_percent: Optional[int]
    recovery_time: Optional[int]
    recovery_time_factor_percent: Optional[int]
    acwr_factor_percent: Optional[int]
    stress_history_factor_percent: Optional[int]
    hrv_factor_percent: Optional[int]
    sleep_history_factor_percent: Optional[int]
    valid_sleep: Optional[bool]
    input_context: Optional[str]
    hrv_weekly_average: Optional[float]
    acute_load: Optional[float]
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class GarminTrainingReadinessValidationIssue:
    source_file: str
    record_index: int
    message: str


@dataclass(frozen=True)
class GarminTrainingReadinessFileSummary:
    source_file: str
    records_seen: int
    records_parsed: int
    records_invalid: int


@dataclass(frozen=True)
class GarminTrainingReadinessImportSummary:
    source_path: Path
    parser_version: str
    source_files: tuple[str, ...]
    file_summaries: tuple[GarminTrainingReadinessFileSummary, ...]
    records: tuple[ParsedGarminTrainingReadiness, ...]
    validation_issues: tuple[GarminTrainingReadinessValidationIssue, ...]
    levels_seen: tuple[str, ...]

    @property
    def file_count(self) -> int:
        return len(self.source_files)

    @property
    def records_seen(self) -> int:
        return sum(summary.records_seen for summary in self.file_summaries)

    @property
    def records_parsed(self) -> int:
        return len(self.records)

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
            "source_files": list(self.source_files),
            "levels_seen": list(self.levels_seen),
        }


def load_training_readiness_from_zip(
    source_path: Union[Path, str],
    source_files: Optional[Iterable[str]] = None,
) -> GarminTrainingReadinessImportSummary:
    export_path = Path(source_path)
    if source_files is None:
        inspection = inspect_garmin_export_zip(export_path)
        selected_source_files = inspection.training_readiness_files
    else:
        selected_source_files = tuple(sorted(source_files))

    records: list[ParsedGarminTrainingReadiness] = []
    validation_issues: list[GarminTrainingReadinessValidationIssue] = []
    file_summaries: list[GarminTrainingReadinessFileSummary] = []
    levels_seen: set[str] = set()

    try:
        with ZipFile(export_path) as archive:
            archive_names = set(archive.namelist())
            for source_file in selected_source_files:
                if source_file not in archive_names:
                    raise GarminTrainingReadinessError(f"Training readiness file is missing from ZIP: {source_file}")

                payload = _read_json_from_zip(archive, source_file)
                candidate_records = _extract_records(payload, source_file)
                parsed_count_before = len(records)
                invalid_count_before = len(validation_issues)

                for record_index, raw_record in enumerate(candidate_records):
                    parsed_record = _parse_record(raw_record, source_file, record_index)
                    if isinstance(parsed_record, GarminTrainingReadinessValidationIssue):
                        validation_issues.append(parsed_record)
                        continue

                    records.append(parsed_record)
                    levels_seen.add(parsed_record.level)

                file_summaries.append(
                    GarminTrainingReadinessFileSummary(
                        source_file=source_file,
                        records_seen=len(candidate_records),
                        records_parsed=len(records) - parsed_count_before,
                        records_invalid=len(validation_issues) - invalid_count_before,
                    )
                )
    except BadZipFile as exc:
        raise GarminTrainingReadinessError(f"Invalid Garmin export ZIP: {export_path}") from exc

    return GarminTrainingReadinessImportSummary(
        source_path=export_path,
        parser_version=PARSER_VERSION,
        source_files=selected_source_files,
        file_summaries=tuple(file_summaries),
        records=tuple(records),
        validation_issues=tuple(validation_issues),
        levels_seen=tuple(sorted(levels_seen)),
    )


def _read_json_from_zip(archive: ZipFile, source_file: str) -> object:
    try:
        with archive.open(source_file) as file_handle:
            return json.load(file_handle)
    except json.JSONDecodeError as exc:
        raise GarminTrainingReadinessError(f"Invalid JSON in training readiness file: {source_file}") from exc


def _extract_records(payload: object, source_file: str) -> list[dict[str, Any]]:
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise GarminTrainingReadinessError(f"Unsupported training readiness JSON structure: {source_file}")


def _parse_record(
    raw_record: dict[str, Any],
    source_file: str,
    record_index: int,
) -> Union[ParsedGarminTrainingReadiness, GarminTrainingReadinessValidationIssue]:
    try:
        record = GarminTrainingReadinessRecord.model_validate(raw_record)
    except ValidationError as exc:
        return GarminTrainingReadinessValidationIssue(
            source_file=source_file,
            record_index=record_index,
            message=str(exc),
        )

    return ParsedGarminTrainingReadiness(
        provider=GARMIN_PROVIDER,
        parser_version=PARSER_VERSION,
        source_file=source_file,
        source_record_id=record.calendar_date.isoformat(),
        calendar_date=record.calendar_date,
        timestamp=record.timestamp,
        timestamp_local=record.timestamp_local,
        level=record.level,
        score=record.score,
        feedback_short=record.feedback_short,
        feedback_long=record.feedback_long,
        sleep_score=record.sleep_score,
        sleep_score_factor_percent=record.sleep_score_factor_percent,
        recovery_time=record.recovery_time,
        recovery_time_factor_percent=record.recovery_time_factor_percent,
        acwr_factor_percent=record.acwr_factor_percent,
        stress_history_factor_percent=record.stress_history_factor_percent,
        hrv_factor_percent=record.hrv_factor_percent,
        sleep_history_factor_percent=record.sleep_history_factor_percent,
        valid_sleep=record.valid_sleep,
        input_context=record.input_context,
        hrv_weekly_average=record.hrv_weekly_average,
        acute_load=record.acute_load,
        raw_payload=raw_record,
    )
