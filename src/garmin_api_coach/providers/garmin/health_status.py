import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional, Union
from zipfile import BadZipFile, ZipFile

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from garmin_api_coach.providers.garmin.export_inspector import inspect_garmin_export_zip
from garmin_api_coach.providers.garmin.summarized_activities import GARMIN_PROVIDER


PARSER_VERSION = "garmin_health_status_v1"


class GarminHealthStatusError(ValueError):
    """Raised when Garmin health-status records cannot be parsed."""


class GarminHealthStatusMetric(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: str
    value: Optional[float] = None
    baseline_upper_limit: Optional[float] = Field(default=None, alias="baselineUpperLimit")
    baseline_lower_limit: Optional[float] = Field(default=None, alias="baselineLowerLimit")
    status: Optional[str] = None
    percentage: Optional[float] = None
    feedback_key: Optional[str] = Field(default=None, alias="feedbackKey")


class GarminHealthStatusRecord(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    calendar_date: date = Field(alias="calendarDate")
    create_timestamp_utc: Optional[datetime] = Field(default=None, alias="createTimestampUTC")
    update_timestamp_utc: Optional[datetime] = Field(default=None, alias="updateTimestampUTC")
    outliers_count: Optional[int] = Field(default=None, alias="outliersCount")
    metrics: list[GarminHealthStatusMetric] = Field(default_factory=list)


@dataclass(frozen=True)
class ParsedGarminHealthStatus:
    provider: str
    parser_version: str
    source_file: str
    source_record_id: str
    calendar_date: date
    create_timestamp_utc: Optional[datetime]
    update_timestamp_utc: Optional[datetime]
    outliers_count: Optional[int]
    heart_rate_value: Optional[float]
    heart_rate_status: Optional[str]
    heart_rate_baseline_lower: Optional[float]
    heart_rate_baseline_upper: Optional[float]
    hrv_value: Optional[float]
    hrv_status: Optional[str]
    hrv_baseline_lower: Optional[float]
    hrv_baseline_upper: Optional[float]
    respiration_value: Optional[float]
    respiration_status: Optional[str]
    spo2_value: Optional[float]
    spo2_status: Optional[str]
    skin_temp_c_value: Optional[float]
    skin_temp_c_status: Optional[str]
    metric_types: tuple[str, ...]
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class GarminHealthStatusValidationIssue:
    source_file: str
    record_index: int
    message: str


@dataclass(frozen=True)
class GarminHealthStatusFileSummary:
    source_file: str
    records_seen: int
    records_parsed: int
    records_invalid: int


@dataclass(frozen=True)
class GarminHealthStatusImportSummary:
    source_path: Path
    parser_version: str
    source_files: tuple[str, ...]
    file_summaries: tuple[GarminHealthStatusFileSummary, ...]
    records: tuple[ParsedGarminHealthStatus, ...]
    validation_issues: tuple[GarminHealthStatusValidationIssue, ...]
    metric_types_seen: tuple[str, ...]

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
            "metric_types_seen": list(self.metric_types_seen),
        }


def load_health_status_from_zip(
    source_path: Union[Path, str],
    source_files: Optional[Iterable[str]] = None,
) -> GarminHealthStatusImportSummary:
    export_path = Path(source_path)
    if source_files is None:
        inspection = inspect_garmin_export_zip(export_path)
        selected_source_files = inspection.health_status_files
    else:
        selected_source_files = tuple(sorted(source_files))

    records: list[ParsedGarminHealthStatus] = []
    validation_issues: list[GarminHealthStatusValidationIssue] = []
    file_summaries: list[GarminHealthStatusFileSummary] = []
    metric_types_seen: set[str] = set()

    try:
        with ZipFile(export_path) as archive:
            archive_names = set(archive.namelist())
            for source_file in selected_source_files:
                if source_file not in archive_names:
                    raise GarminHealthStatusError(f"Health-status file is missing from ZIP: {source_file}")

                payload = _read_json_from_zip(archive, source_file)
                candidate_records = _extract_records(payload, source_file)
                parsed_count_before = len(records)
                invalid_count_before = len(validation_issues)

                for record_index, raw_record in enumerate(candidate_records):
                    parsed_record = _parse_record(raw_record, source_file, record_index)
                    if isinstance(parsed_record, GarminHealthStatusValidationIssue):
                        validation_issues.append(parsed_record)
                        continue

                    records.append(parsed_record)
                    metric_types_seen.update(parsed_record.metric_types)

                file_summaries.append(
                    GarminHealthStatusFileSummary(
                        source_file=source_file,
                        records_seen=len(candidate_records),
                        records_parsed=len(records) - parsed_count_before,
                        records_invalid=len(validation_issues) - invalid_count_before,
                    )
                )
    except BadZipFile as exc:
        raise GarminHealthStatusError(f"Invalid Garmin export ZIP: {export_path}") from exc

    return GarminHealthStatusImportSummary(
        source_path=export_path,
        parser_version=PARSER_VERSION,
        source_files=selected_source_files,
        file_summaries=tuple(file_summaries),
        records=tuple(records),
        validation_issues=tuple(validation_issues),
        metric_types_seen=tuple(sorted(metric_types_seen)),
    )


def _read_json_from_zip(archive: ZipFile, source_file: str) -> object:
    try:
        with archive.open(source_file) as file_handle:
            return json.load(file_handle)
    except json.JSONDecodeError as exc:
        raise GarminHealthStatusError(f"Invalid JSON in health-status file: {source_file}") from exc


def _extract_records(payload: object, source_file: str) -> list[dict[str, Any]]:
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise GarminHealthStatusError(f"Unsupported health-status JSON structure: {source_file}")


def _parse_record(
    raw_record: dict[str, Any],
    source_file: str,
    record_index: int,
) -> Union[ParsedGarminHealthStatus, GarminHealthStatusValidationIssue]:
    try:
        record = GarminHealthStatusRecord.model_validate(raw_record)
    except ValidationError as exc:
        return GarminHealthStatusValidationIssue(
            source_file=source_file,
            record_index=record_index,
            message=str(exc),
        )

    metrics_by_type = {metric.type.upper(): metric for metric in record.metrics}
    heart_rate = metrics_by_type.get("HR")
    hrv = metrics_by_type.get("HRV")
    respiration = metrics_by_type.get("RESPIRATION")
    spo2 = metrics_by_type.get("SPO2")
    skin_temp_c = metrics_by_type.get("SKIN_TEMP_C")

    return ParsedGarminHealthStatus(
        provider=GARMIN_PROVIDER,
        parser_version=PARSER_VERSION,
        source_file=source_file,
        source_record_id=record.calendar_date.isoformat(),
        calendar_date=record.calendar_date,
        create_timestamp_utc=record.create_timestamp_utc,
        update_timestamp_utc=record.update_timestamp_utc,
        outliers_count=record.outliers_count,
        heart_rate_value=_metric_value(heart_rate),
        heart_rate_status=_metric_status(heart_rate),
        heart_rate_baseline_lower=_metric_baseline_lower(heart_rate),
        heart_rate_baseline_upper=_metric_baseline_upper(heart_rate),
        hrv_value=_metric_value(hrv),
        hrv_status=_metric_status(hrv),
        hrv_baseline_lower=_metric_baseline_lower(hrv),
        hrv_baseline_upper=_metric_baseline_upper(hrv),
        respiration_value=_metric_value(respiration),
        respiration_status=_metric_status(respiration),
        spo2_value=_metric_value(spo2),
        spo2_status=_metric_status(spo2),
        skin_temp_c_value=_metric_value(skin_temp_c),
        skin_temp_c_status=_metric_status(skin_temp_c),
        metric_types=tuple(sorted(metrics_by_type)),
        raw_payload=raw_record,
    )


def _metric_value(metric: Optional[GarminHealthStatusMetric]) -> Optional[float]:
    return metric.value if metric is not None else None


def _metric_status(metric: Optional[GarminHealthStatusMetric]) -> Optional[str]:
    return metric.status if metric is not None else None


def _metric_baseline_lower(metric: Optional[GarminHealthStatusMetric]) -> Optional[float]:
    return metric.baseline_lower_limit if metric is not None else None


def _metric_baseline_upper(metric: Optional[GarminHealthStatusMetric]) -> Optional[float]:
    return metric.baseline_upper_limit if metric is not None else None
