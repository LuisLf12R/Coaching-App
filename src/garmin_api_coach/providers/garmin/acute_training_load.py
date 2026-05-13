import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Union
from zipfile import BadZipFile, ZipFile

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from garmin_api_coach.providers.garmin.export_inspector import inspect_garmin_export_zip
from garmin_api_coach.providers.garmin.summarized_activities import GARMIN_PROVIDER


PARSER_VERSION = "garmin_acute_training_load_v1"


class GarminAcuteTrainingLoadError(ValueError):
    """Raised when Garmin acute training load records cannot be parsed."""


class GarminAcuteTrainingLoadRecord(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    calendar_date: date = Field(alias="calendarDate")
    timestamp: Optional[datetime] = None
    acwr_percent: Optional[int] = Field(default=None, alias="acwrPercent")
    acwr_status: Optional[str] = Field(default=None, alias="acwrStatus")
    acwr_status_feedback: Optional[str] = Field(default=None, alias="acwrStatusFeedback")
    daily_training_load_acute: Optional[float] = Field(default=None, alias="dailyTrainingLoadAcute")
    daily_training_load_chronic: Optional[float] = Field(default=None, alias="dailyTrainingLoadChronic")
    daily_acute_chronic_workload_ratio: Optional[float] = Field(
        default=None,
        alias="dailyAcuteChronicWorkloadRatio",
    )

    @field_validator("calendar_date", mode="before")
    @classmethod
    def parse_calendar_date(cls, value: object) -> object:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date()
        return value

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: object) -> object:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        return value


@dataclass(frozen=True)
class ParsedGarminAcuteTrainingLoad:
    provider: str
    parser_version: str
    source_file: str
    source_record_id: str
    calendar_date: date
    timestamp: Optional[datetime]
    acwr_percent: Optional[int]
    acwr_status: Optional[str]
    acwr_status_feedback: Optional[str]
    daily_training_load_acute: Optional[float]
    daily_training_load_chronic: Optional[float]
    daily_acute_chronic_workload_ratio: Optional[float]
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class GarminAcuteTrainingLoadValidationIssue:
    source_file: str
    record_index: int
    message: str


@dataclass(frozen=True)
class GarminAcuteTrainingLoadFileSummary:
    source_file: str
    records_seen: int
    records_parsed: int
    records_invalid: int


@dataclass(frozen=True)
class GarminAcuteTrainingLoadImportSummary:
    source_path: Path
    parser_version: str
    source_files: tuple[str, ...]
    file_summaries: tuple[GarminAcuteTrainingLoadFileSummary, ...]
    records: tuple[ParsedGarminAcuteTrainingLoad, ...]
    validation_issues: tuple[GarminAcuteTrainingLoadValidationIssue, ...]
    statuses_seen: tuple[str, ...]

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
            "statuses_seen": list(self.statuses_seen),
        }


def load_acute_training_load_from_zip(
    source_path: Union[Path, str],
    source_files: Optional[Iterable[str]] = None,
) -> GarminAcuteTrainingLoadImportSummary:
    export_path = Path(source_path)
    if source_files is None:
        inspection = inspect_garmin_export_zip(export_path)
        selected_source_files = inspection.acute_training_load_files
    else:
        selected_source_files = tuple(sorted(source_files))

    records: list[ParsedGarminAcuteTrainingLoad] = []
    validation_issues: list[GarminAcuteTrainingLoadValidationIssue] = []
    file_summaries: list[GarminAcuteTrainingLoadFileSummary] = []
    statuses_seen: set[str] = set()

    try:
        with ZipFile(export_path) as archive:
            archive_names = set(archive.namelist())
            for source_file in selected_source_files:
                if source_file not in archive_names:
                    raise GarminAcuteTrainingLoadError(f"Acute training load file is missing from ZIP: {source_file}")

                payload = _read_json_from_zip(archive, source_file)
                candidate_records = _extract_records(payload, source_file)
                parsed_count_before = len(records)
                invalid_count_before = len(validation_issues)

                for record_index, raw_record in enumerate(candidate_records):
                    parsed_record = _parse_record(raw_record, source_file, record_index)
                    if isinstance(parsed_record, GarminAcuteTrainingLoadValidationIssue):
                        validation_issues.append(parsed_record)
                        continue

                    records.append(parsed_record)
                    if parsed_record.acwr_status:
                        statuses_seen.add(parsed_record.acwr_status)

                file_summaries.append(
                    GarminAcuteTrainingLoadFileSummary(
                        source_file=source_file,
                        records_seen=len(candidate_records),
                        records_parsed=len(records) - parsed_count_before,
                        records_invalid=len(validation_issues) - invalid_count_before,
                    )
                )
    except BadZipFile as exc:
        raise GarminAcuteTrainingLoadError(f"Invalid Garmin export ZIP: {export_path}") from exc

    return GarminAcuteTrainingLoadImportSummary(
        source_path=export_path,
        parser_version=PARSER_VERSION,
        source_files=selected_source_files,
        file_summaries=tuple(file_summaries),
        records=tuple(records),
        validation_issues=tuple(validation_issues),
        statuses_seen=tuple(sorted(statuses_seen)),
    )


def _read_json_from_zip(archive: ZipFile, source_file: str) -> object:
    try:
        with archive.open(source_file) as file_handle:
            return json.load(file_handle)
    except json.JSONDecodeError as exc:
        raise GarminAcuteTrainingLoadError(f"Invalid JSON in acute training load file: {source_file}") from exc


def _extract_records(payload: object, source_file: str) -> list[dict[str, Any]]:
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise GarminAcuteTrainingLoadError(f"Unsupported acute training load JSON structure: {source_file}")


def _parse_record(
    raw_record: dict[str, Any],
    source_file: str,
    record_index: int,
) -> Union[ParsedGarminAcuteTrainingLoad, GarminAcuteTrainingLoadValidationIssue]:
    try:
        record = GarminAcuteTrainingLoadRecord.model_validate(raw_record)
    except ValidationError as exc:
        return GarminAcuteTrainingLoadValidationIssue(
            source_file=source_file,
            record_index=record_index,
            message=str(exc),
        )

    return ParsedGarminAcuteTrainingLoad(
        provider=GARMIN_PROVIDER,
        parser_version=PARSER_VERSION,
        source_file=source_file,
        source_record_id=record.calendar_date.isoformat(),
        calendar_date=record.calendar_date,
        timestamp=record.timestamp,
        acwr_percent=record.acwr_percent,
        acwr_status=record.acwr_status,
        acwr_status_feedback=record.acwr_status_feedback,
        daily_training_load_acute=record.daily_training_load_acute,
        daily_training_load_chronic=record.daily_training_load_chronic,
        daily_acute_chronic_workload_ratio=record.daily_acute_chronic_workload_ratio,
        raw_payload=raw_record,
    )
