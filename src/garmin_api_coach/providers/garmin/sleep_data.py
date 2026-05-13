import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional, Union
from zipfile import BadZipFile, ZipFile

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from garmin_api_coach.providers.garmin.export_inspector import inspect_garmin_export_zip
from garmin_api_coach.providers.garmin.summarized_activities import GARMIN_PROVIDER


PARSER_VERSION = "garmin_sleep_data_v1"


class GarminSleepDataError(ValueError):
    """Raised when Garmin sleep records cannot be parsed."""


class GarminSleepScores(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    overall_score: Optional[int] = Field(default=None, alias="overallScore")
    quality_score: Optional[int] = Field(default=None, alias="qualityScore")
    duration_score: Optional[int] = Field(default=None, alias="durationScore")
    recovery_score: Optional[int] = Field(default=None, alias="recoveryScore")
    restfulness_score: Optional[int] = Field(default=None, alias="restfulnessScore")
    feedback: Optional[str] = None
    insight: Optional[str] = None


class GarminSleepRecord(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    calendar_date: date = Field(alias="calendarDate")
    sleep_start_gmt: Optional[datetime] = Field(default=None, alias="sleepStartTimestampGMT")
    sleep_end_gmt: Optional[datetime] = Field(default=None, alias="sleepEndTimestampGMT")
    deep_sleep_seconds: Optional[int] = Field(default=None, alias="deepSleepSeconds")
    light_sleep_seconds: Optional[int] = Field(default=None, alias="lightSleepSeconds")
    rem_sleep_seconds: Optional[int] = Field(default=None, alias="remSleepSeconds")
    awake_sleep_seconds: Optional[int] = Field(default=None, alias="awakeSleepSeconds")
    unmeasurable_seconds: Optional[int] = Field(default=None, alias="unmeasurableSeconds")
    awake_count: Optional[int] = Field(default=None, alias="awakeCount")
    restless_moment_count: Optional[int] = Field(default=None, alias="restlessMomentCount")
    avg_sleep_stress: Optional[float] = Field(default=None, alias="avgSleepStress")
    average_respiration: Optional[float] = Field(default=None, alias="averageRespiration")
    lowest_respiration: Optional[float] = Field(default=None, alias="lowestRespiration")
    highest_respiration: Optional[float] = Field(default=None, alias="highestRespiration")
    sleep_scores: Optional[GarminSleepScores] = Field(default=None, alias="sleepScores")


@dataclass(frozen=True)
class ParsedGarminSleepMetric:
    provider: str
    parser_version: str
    source_file: str
    source_record_id: str
    calendar_date: date
    sleep_start_gmt: Optional[datetime]
    sleep_end_gmt: Optional[datetime]
    deep_sleep_seconds: Optional[int]
    light_sleep_seconds: Optional[int]
    rem_sleep_seconds: Optional[int]
    awake_sleep_seconds: Optional[int]
    unmeasurable_seconds: Optional[int]
    awake_count: Optional[int]
    restless_moment_count: Optional[int]
    avg_sleep_stress: Optional[float]
    average_respiration: Optional[float]
    lowest_respiration: Optional[float]
    highest_respiration: Optional[float]
    overall_score: Optional[int]
    quality_score: Optional[int]
    duration_score: Optional[int]
    recovery_score: Optional[int]
    restfulness_score: Optional[int]
    feedback: Optional[str]
    insight: Optional[str]
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class GarminSleepValidationIssue:
    source_file: str
    record_index: int
    message: str


@dataclass(frozen=True)
class GarminSleepFileSummary:
    source_file: str
    records_seen: int
    records_parsed: int
    records_invalid: int


@dataclass(frozen=True)
class GarminSleepImportSummary:
    source_path: Path
    parser_version: str
    source_files: tuple[str, ...]
    file_summaries: tuple[GarminSleepFileSummary, ...]
    records: tuple[ParsedGarminSleepMetric, ...]
    validation_issues: tuple[GarminSleepValidationIssue, ...]

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
        }


def load_sleep_data_from_zip(
    source_path: Union[Path, str],
    source_files: Optional[Iterable[str]] = None,
) -> GarminSleepImportSummary:
    export_path = Path(source_path)
    if source_files is None:
        inspection = inspect_garmin_export_zip(export_path)
        selected_source_files = inspection.sleep_data_files
    else:
        selected_source_files = tuple(sorted(source_files))

    records: list[ParsedGarminSleepMetric] = []
    validation_issues: list[GarminSleepValidationIssue] = []
    file_summaries: list[GarminSleepFileSummary] = []

    try:
        with ZipFile(export_path) as archive:
            archive_names = set(archive.namelist())
            for source_file in selected_source_files:
                if source_file not in archive_names:
                    raise GarminSleepDataError(f"Sleep data file is missing from ZIP: {source_file}")

                payload = _read_json_from_zip(archive, source_file)
                candidate_records = _extract_records(payload, source_file)
                parsed_count_before = len(records)
                invalid_count_before = len(validation_issues)

                for record_index, raw_record in enumerate(candidate_records):
                    parsed_record = _parse_record(raw_record, source_file, record_index)
                    if isinstance(parsed_record, GarminSleepValidationIssue):
                        validation_issues.append(parsed_record)
                        continue

                    records.append(parsed_record)

                file_summaries.append(
                    GarminSleepFileSummary(
                        source_file=source_file,
                        records_seen=len(candidate_records),
                        records_parsed=len(records) - parsed_count_before,
                        records_invalid=len(validation_issues) - invalid_count_before,
                    )
                )
    except BadZipFile as exc:
        raise GarminSleepDataError(f"Invalid Garmin export ZIP: {export_path}") from exc

    return GarminSleepImportSummary(
        source_path=export_path,
        parser_version=PARSER_VERSION,
        source_files=selected_source_files,
        file_summaries=tuple(file_summaries),
        records=tuple(records),
        validation_issues=tuple(validation_issues),
    )


def _read_json_from_zip(archive: ZipFile, source_file: str) -> object:
    try:
        with archive.open(source_file) as file_handle:
            return json.load(file_handle)
    except json.JSONDecodeError as exc:
        raise GarminSleepDataError(f"Invalid JSON in sleep data file: {source_file}") from exc


def _extract_records(payload: object, source_file: str) -> list[dict[str, Any]]:
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise GarminSleepDataError(f"Unsupported sleep data JSON structure: {source_file}")


def _parse_record(
    raw_record: dict[str, Any],
    source_file: str,
    record_index: int,
) -> Union[ParsedGarminSleepMetric, GarminSleepValidationIssue]:
    try:
        record = GarminSleepRecord.model_validate(raw_record)
    except ValidationError as exc:
        return GarminSleepValidationIssue(
            source_file=source_file,
            record_index=record_index,
            message=str(exc),
        )

    scores = record.sleep_scores
    return ParsedGarminSleepMetric(
        provider=GARMIN_PROVIDER,
        parser_version=PARSER_VERSION,
        source_file=source_file,
        source_record_id=record.calendar_date.isoformat(),
        calendar_date=record.calendar_date,
        sleep_start_gmt=record.sleep_start_gmt,
        sleep_end_gmt=record.sleep_end_gmt,
        deep_sleep_seconds=record.deep_sleep_seconds,
        light_sleep_seconds=record.light_sleep_seconds,
        rem_sleep_seconds=record.rem_sleep_seconds,
        awake_sleep_seconds=record.awake_sleep_seconds,
        unmeasurable_seconds=record.unmeasurable_seconds,
        awake_count=record.awake_count,
        restless_moment_count=record.restless_moment_count,
        avg_sleep_stress=record.avg_sleep_stress,
        average_respiration=record.average_respiration,
        lowest_respiration=record.lowest_respiration,
        highest_respiration=record.highest_respiration,
        overall_score=scores.overall_score if scores is not None else None,
        quality_score=scores.quality_score if scores is not None else None,
        duration_score=scores.duration_score if scores is not None else None,
        recovery_score=scores.recovery_score if scores is not None else None,
        restfulness_score=scores.restfulness_score if scores is not None else None,
        feedback=scores.feedback if scores is not None else None,
        insight=scores.insight if scores is not None else None,
        raw_payload=raw_record,
    )
