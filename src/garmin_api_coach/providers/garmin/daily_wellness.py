import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Optional, Union
from zipfile import BadZipFile, ZipFile

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from garmin_api_coach.providers.garmin.export_inspector import inspect_garmin_export_zip
from garmin_api_coach.providers.garmin.summarized_activities import GARMIN_PROVIDER


PARSER_VERSION = "garmin_daily_wellness_v1"


class GarminDailyWellnessError(ValueError):
    """Raised when Garmin UDS daily wellness records cannot be parsed."""


class GarminStressAggregate(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: str
    average_stress_level: Optional[int] = Field(default=None, alias="averageStressLevel")
    max_stress_level: Optional[int] = Field(default=None, alias="maxStressLevel")
    stress_duration: Optional[int] = Field(default=None, alias="stressDuration")
    rest_duration: Optional[int] = Field(default=None, alias="restDuration")


class GarminAllDayStress(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    aggregator_list: list[GarminStressAggregate] = Field(default_factory=list, alias="aggregatorList")


class GarminBodyBatteryStat(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    body_battery_stat_type: str = Field(alias="bodyBatteryStatType")
    stats_value: Optional[int] = Field(default=None, alias="statsValue")


class GarminBodyBattery(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    charged_value: Optional[int] = Field(default=None, alias="chargedValue")
    drained_value: Optional[int] = Field(default=None, alias="drainedValue")
    body_battery_stat_list: list[GarminBodyBatteryStat] = Field(default_factory=list, alias="bodyBatteryStatList")


class GarminRespiration(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    avg_waking_respiration_value: Optional[float] = Field(default=None, alias="avgWakingRespirationValue")


class GarminDailyWellnessRecord(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    calendar_date: date = Field(alias="calendarDate")
    total_steps: Optional[int] = Field(default=None, alias="totalSteps")
    daily_step_goal: Optional[int] = Field(default=None, alias="dailyStepGoal")
    wellness_distance_meters: Optional[float] = Field(default=None, alias="wellnessDistanceMeters")
    resting_heart_rate: Optional[int] = Field(default=None, alias="restingHeartRate")
    current_day_resting_heart_rate: Optional[int] = Field(default=None, alias="currentDayRestingHeartRate")
    min_heart_rate: Optional[int] = Field(default=None, alias="minHeartRate")
    max_heart_rate: Optional[int] = Field(default=None, alias="maxHeartRate")
    moderate_intensity_minutes: Optional[int] = Field(default=None, alias="moderateIntensityMinutes")
    vigorous_intensity_minutes: Optional[int] = Field(default=None, alias="vigorousIntensityMinutes")
    all_day_stress: Optional[GarminAllDayStress] = Field(default=None, alias="allDayStress")
    body_battery: Optional[GarminBodyBattery] = Field(default=None, alias="bodyBattery")
    respiration: Optional[GarminRespiration] = None
    average_spo2: Optional[float] = Field(default=None, alias="averageSpo2Value")
    lowest_spo2: Optional[int] = Field(default=None, alias="lowestSpo2Value")
    latest_spo2: Optional[int] = Field(default=None, alias="latestSpo2Value")


@dataclass(frozen=True)
class ParsedGarminDailyWellness:
    provider: str
    parser_version: str
    source_file: str
    source_record_id: str
    calendar_date: date
    total_steps: Optional[int]
    daily_step_goal: Optional[int]
    wellness_distance_meters: Optional[float]
    resting_heart_rate: Optional[int]
    current_day_resting_heart_rate: Optional[int]
    min_heart_rate: Optional[int]
    max_heart_rate: Optional[int]
    moderate_intensity_minutes: Optional[int]
    vigorous_intensity_minutes: Optional[int]
    average_stress_level: Optional[int]
    max_stress_level: Optional[int]
    stress_duration_seconds: Optional[int]
    rest_duration_seconds: Optional[int]
    body_battery_charged: Optional[int]
    body_battery_drained: Optional[int]
    body_battery_highest: Optional[int]
    body_battery_lowest: Optional[int]
    body_battery_most_recent: Optional[int]
    body_battery_start_of_day: Optional[int]
    body_battery_end_of_day: Optional[int]
    average_waking_respiration: Optional[float]
    average_spo2: Optional[float]
    lowest_spo2: Optional[int]
    latest_spo2: Optional[int]
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class GarminDailyWellnessValidationIssue:
    source_file: str
    record_index: int
    message: str


@dataclass(frozen=True)
class GarminDailyWellnessFileSummary:
    source_file: str
    records_seen: int
    records_parsed: int
    records_invalid: int


@dataclass(frozen=True)
class GarminDailyWellnessImportSummary:
    source_path: Path
    parser_version: str
    source_files: tuple[str, ...]
    file_summaries: tuple[GarminDailyWellnessFileSummary, ...]
    records: tuple[ParsedGarminDailyWellness, ...]
    validation_issues: tuple[GarminDailyWellnessValidationIssue, ...]

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


def load_daily_wellness_from_zip(
    source_path: Union[Path, str],
    source_files: Optional[Iterable[str]] = None,
) -> GarminDailyWellnessImportSummary:
    export_path = Path(source_path)
    if source_files is None:
        inspection = inspect_garmin_export_zip(export_path)
        selected_source_files = inspection.uds_aggregator_files
    else:
        selected_source_files = tuple(sorted(source_files))

    records: list[ParsedGarminDailyWellness] = []
    validation_issues: list[GarminDailyWellnessValidationIssue] = []
    file_summaries: list[GarminDailyWellnessFileSummary] = []

    try:
        with ZipFile(export_path) as archive:
            archive_names = set(archive.namelist())
            for source_file in selected_source_files:
                if source_file not in archive_names:
                    raise GarminDailyWellnessError(f"UDS aggregator file is missing from ZIP: {source_file}")

                payload = _read_json_from_zip(archive, source_file)
                candidate_records = _extract_records(payload, source_file)
                parsed_count_before = len(records)
                invalid_count_before = len(validation_issues)

                for record_index, raw_record in enumerate(candidate_records):
                    parsed_record = _parse_record(raw_record, source_file, record_index)
                    if isinstance(parsed_record, GarminDailyWellnessValidationIssue):
                        validation_issues.append(parsed_record)
                        continue
                    if parsed_record is not None:
                        records.append(parsed_record)

                file_summaries.append(
                    GarminDailyWellnessFileSummary(
                        source_file=source_file,
                        records_seen=len(candidate_records),
                        records_parsed=len(records) - parsed_count_before,
                        records_invalid=len(validation_issues) - invalid_count_before,
                    )
                )
    except BadZipFile as exc:
        raise GarminDailyWellnessError(f"Invalid Garmin export ZIP: {export_path}") from exc

    return GarminDailyWellnessImportSummary(
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
        raise GarminDailyWellnessError(f"Invalid JSON in UDS aggregator file: {source_file}") from exc


def _extract_records(payload: object, source_file: str) -> list[dict[str, Any]]:
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise GarminDailyWellnessError(f"Unsupported UDS aggregator JSON structure: {source_file}")


def _parse_record(
    raw_record: dict[str, Any],
    source_file: str,
    record_index: int,
) -> Union[ParsedGarminDailyWellness, GarminDailyWellnessValidationIssue, None]:
    try:
        record = GarminDailyWellnessRecord.model_validate(raw_record)
    except ValidationError as exc:
        return GarminDailyWellnessValidationIssue(
            source_file=source_file,
            record_index=record_index,
            message=str(exc),
        )

    if not _has_wellness_signal(record):
        return None

    total_stress = _total_stress(record.all_day_stress)
    battery_stats = _body_battery_stats(record.body_battery)

    return ParsedGarminDailyWellness(
        provider=GARMIN_PROVIDER,
        parser_version=PARSER_VERSION,
        source_file=source_file,
        source_record_id=record.calendar_date.isoformat(),
        calendar_date=record.calendar_date,
        total_steps=record.total_steps,
        daily_step_goal=record.daily_step_goal,
        wellness_distance_meters=record.wellness_distance_meters,
        resting_heart_rate=record.resting_heart_rate,
        current_day_resting_heart_rate=record.current_day_resting_heart_rate,
        min_heart_rate=record.min_heart_rate,
        max_heart_rate=record.max_heart_rate,
        moderate_intensity_minutes=record.moderate_intensity_minutes,
        vigorous_intensity_minutes=record.vigorous_intensity_minutes,
        average_stress_level=total_stress.average_stress_level if total_stress is not None else None,
        max_stress_level=total_stress.max_stress_level if total_stress is not None else None,
        stress_duration_seconds=total_stress.stress_duration if total_stress is not None else None,
        rest_duration_seconds=total_stress.rest_duration if total_stress is not None else None,
        body_battery_charged=record.body_battery.charged_value if record.body_battery is not None else None,
        body_battery_drained=record.body_battery.drained_value if record.body_battery is not None else None,
        body_battery_highest=battery_stats.get("HIGHEST"),
        body_battery_lowest=battery_stats.get("LOWEST"),
        body_battery_most_recent=battery_stats.get("MOSTRECENT"),
        body_battery_start_of_day=battery_stats.get("STARTOFDAY"),
        body_battery_end_of_day=battery_stats.get("ENDOFDAY"),
        average_waking_respiration=(
            record.respiration.avg_waking_respiration_value if record.respiration is not None else None
        ),
        average_spo2=record.average_spo2,
        lowest_spo2=record.lowest_spo2,
        latest_spo2=record.latest_spo2,
        raw_payload=raw_record,
    )


def _has_wellness_signal(record: GarminDailyWellnessRecord) -> bool:
    return any(
        value is not None
        for value in (
            record.total_steps,
            record.resting_heart_rate,
            record.current_day_resting_heart_rate,
            record.average_spo2,
        )
    ) or bool(record.all_day_stress and record.all_day_stress.aggregator_list) or bool(
        record.body_battery and record.body_battery.body_battery_stat_list
    )


def _total_stress(stress: Optional[GarminAllDayStress]) -> Optional[GarminStressAggregate]:
    if stress is None:
        return None
    for aggregate in stress.aggregator_list:
        if aggregate.type.upper() == "TOTAL":
            return aggregate
    return None


def _body_battery_stats(body_battery: Optional[GarminBodyBattery]) -> dict[str, int]:
    if body_battery is None:
        return {}
    return {
        stat.body_battery_stat_type.upper(): stat.stats_value
        for stat in body_battery.body_battery_stat_list
        if stat.stats_value is not None
    }
