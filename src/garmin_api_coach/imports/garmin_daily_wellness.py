from dataclasses import dataclass
from pathlib import Path
from typing import Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from garmin_api_coach.db.models import Client, DailyWellnessMetric, DataImport, RawRecord
from garmin_api_coach.providers.garmin.daily_wellness import (
    ParsedGarminDailyWellness,
    load_daily_wellness_from_zip,
)
from garmin_api_coach.providers.garmin.summarized_activities import GARMIN_PROVIDER


class GarminDailyWellnessImportError(ValueError):
    """Raised when Garmin UDS daily wellness records cannot be imported."""


@dataclass(frozen=True)
class GarminDailyWellnessDatabaseImportSummary:
    data_import_id: str
    client_id: str
    source_path: Path
    source_name: str
    parser_version: str
    records_seen: int
    records_parsed: int
    records_invalid: int
    raw_records_created: int
    metrics_inserted: int
    metrics_updated: int

    def to_summary(self) -> dict[str, object]:
        return {
            "data_import_id": self.data_import_id,
            "client_id": self.client_id,
            "source_path": str(self.source_path),
            "source_name": self.source_name,
            "parser_version": self.parser_version,
            "records_seen": self.records_seen,
            "records_parsed": self.records_parsed,
            "records_invalid": self.records_invalid,
            "raw_records_created": self.raw_records_created,
            "metrics_inserted": self.metrics_inserted,
            "metrics_updated": self.metrics_updated,
        }


def import_garmin_daily_wellness(
    db: Session,
    *,
    client_id: str,
    source_path: Union[Path, str],
) -> GarminDailyWellnessDatabaseImportSummary:
    client = db.get(Client, client_id)
    if client is None:
        raise GarminDailyWellnessImportError(f"Client does not exist: {client_id}")

    parsed_import = load_daily_wellness_from_zip(source_path)
    source_name = parsed_import.source_path.name

    data_import = DataImport(
        client_id=client.id,
        provider=GARMIN_PROVIDER,
        source_name=source_name,
        source_type="garmin_daily_wellness",
        parser_version=parsed_import.parser_version,
        status="completed" if parsed_import.records_invalid == 0 else "completed_with_warnings",
        summary=parsed_import.to_summary(),
    )
    db.add(data_import)
    db.flush()

    raw_records_created = 0
    metrics_inserted = 0
    metrics_updated = 0

    for parsed_record in parsed_import.records:
        db.add(_raw_record_from_daily_wellness(data_import.id, parsed_record))
        raw_records_created += 1

        existing_metric = db.scalar(
            select(DailyWellnessMetric).where(
                DailyWellnessMetric.provider == parsed_record.provider,
                DailyWellnessMetric.client_id == client.id,
                DailyWellnessMetric.calendar_date == parsed_record.calendar_date,
            )
        )
        if existing_metric is None:
            db.add(_metric_from_parsed(client.id, data_import.id, parsed_record))
            metrics_inserted += 1
        else:
            _update_metric(existing_metric, client.id, data_import.id, parsed_record)
            metrics_updated += 1

    database_summary = GarminDailyWellnessDatabaseImportSummary(
        data_import_id=data_import.id,
        client_id=client.id,
        source_path=parsed_import.source_path,
        source_name=source_name,
        parser_version=parsed_import.parser_version,
        records_seen=parsed_import.records_seen,
        records_parsed=parsed_import.records_parsed,
        records_invalid=parsed_import.records_invalid,
        raw_records_created=raw_records_created,
        metrics_inserted=metrics_inserted,
        metrics_updated=metrics_updated,
    )
    data_import.summary = database_summary.to_summary()
    db.commit()

    return database_summary


def _raw_record_from_daily_wellness(data_import_id: str, record: ParsedGarminDailyWellness) -> RawRecord:
    return RawRecord(
        data_import_id=data_import_id,
        provider=record.provider,
        source_name=record.source_file,
        source_record_id=record.source_record_id,
        parser_version=record.parser_version,
        validation_status="valid",
        payload=record.raw_payload,
    )


def _metric_from_parsed(
    client_id: str,
    data_import_id: str,
    record: ParsedGarminDailyWellness,
) -> DailyWellnessMetric:
    db_metric = DailyWellnessMetric(
        client_id=client_id,
        data_import_id=data_import_id,
        provider=record.provider,
        source_file=record.source_file,
        source_record_id=record.source_record_id,
        calendar_date=record.calendar_date,
    )
    _update_metric(db_metric, client_id, data_import_id, record)
    return db_metric


def _update_metric(
    db_metric: DailyWellnessMetric,
    client_id: str,
    data_import_id: str,
    record: ParsedGarminDailyWellness,
) -> None:
    db_metric.client_id = client_id
    db_metric.data_import_id = data_import_id
    db_metric.source_file = record.source_file
    db_metric.source_record_id = record.source_record_id
    db_metric.calendar_date = record.calendar_date
    db_metric.total_steps = record.total_steps
    db_metric.daily_step_goal = record.daily_step_goal
    db_metric.wellness_distance_meters = record.wellness_distance_meters
    db_metric.resting_heart_rate = record.resting_heart_rate
    db_metric.current_day_resting_heart_rate = record.current_day_resting_heart_rate
    db_metric.min_heart_rate = record.min_heart_rate
    db_metric.max_heart_rate = record.max_heart_rate
    db_metric.moderate_intensity_minutes = record.moderate_intensity_minutes
    db_metric.vigorous_intensity_minutes = record.vigorous_intensity_minutes
    db_metric.average_stress_level = record.average_stress_level
    db_metric.max_stress_level = record.max_stress_level
    db_metric.stress_duration_seconds = record.stress_duration_seconds
    db_metric.rest_duration_seconds = record.rest_duration_seconds
    db_metric.body_battery_charged = record.body_battery_charged
    db_metric.body_battery_drained = record.body_battery_drained
    db_metric.body_battery_highest = record.body_battery_highest
    db_metric.body_battery_lowest = record.body_battery_lowest
    db_metric.body_battery_most_recent = record.body_battery_most_recent
    db_metric.body_battery_start_of_day = record.body_battery_start_of_day
    db_metric.body_battery_end_of_day = record.body_battery_end_of_day
    db_metric.average_waking_respiration = record.average_waking_respiration
    db_metric.average_spo2 = record.average_spo2
    db_metric.lowest_spo2 = record.lowest_spo2
    db_metric.latest_spo2 = record.latest_spo2
    db_metric.provider_metadata = {
        "bodyBatteryCharged": record.body_battery_charged,
        "bodyBatteryDrained": record.body_battery_drained,
        "averageStressLevel": record.average_stress_level,
        "maxStressLevel": record.max_stress_level,
    }
