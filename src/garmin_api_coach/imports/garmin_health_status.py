from dataclasses import dataclass
from pathlib import Path
from typing import Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from garmin_api_coach.db.models import Client, DataImport, HealthStatusMetric, RawRecord
from garmin_api_coach.providers.garmin.health_status import (
    ParsedGarminHealthStatus,
    load_health_status_from_zip,
)
from garmin_api_coach.providers.garmin.summarized_activities import GARMIN_PROVIDER


class GarminHealthStatusImportError(ValueError):
    """Raised when Garmin health-status records cannot be imported."""


@dataclass(frozen=True)
class GarminHealthStatusDatabaseImportSummary:
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
    metric_types_seen: tuple[str, ...]

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
            "metric_types_seen": list(self.metric_types_seen),
        }


def import_garmin_health_status(
    db: Session,
    *,
    client_id: str,
    source_path: Union[Path, str],
) -> GarminHealthStatusDatabaseImportSummary:
    client = db.get(Client, client_id)
    if client is None:
        raise GarminHealthStatusImportError(f"Client does not exist: {client_id}")

    parsed_import = load_health_status_from_zip(source_path)
    source_name = parsed_import.source_path.name

    data_import = DataImport(
        client_id=client.id,
        provider=GARMIN_PROVIDER,
        source_name=source_name,
        source_type="garmin_health_status",
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
        db.add(_raw_record_from_health_status(data_import.id, parsed_record))
        raw_records_created += 1

        existing_metric = db.scalar(
            select(HealthStatusMetric).where(
                HealthStatusMetric.provider == parsed_record.provider,
                HealthStatusMetric.client_id == client.id,
                HealthStatusMetric.calendar_date == parsed_record.calendar_date,
            )
        )
        if existing_metric is None:
            db.add(_metric_from_parsed(client.id, data_import.id, parsed_record))
            metrics_inserted += 1
        else:
            _update_metric(existing_metric, client.id, data_import.id, parsed_record)
            metrics_updated += 1

    database_summary = GarminHealthStatusDatabaseImportSummary(
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
        metric_types_seen=parsed_import.metric_types_seen,
    )
    data_import.summary = database_summary.to_summary()
    db.commit()

    return database_summary


def _raw_record_from_health_status(data_import_id: str, record: ParsedGarminHealthStatus) -> RawRecord:
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
    record: ParsedGarminHealthStatus,
) -> HealthStatusMetric:
    db_metric = HealthStatusMetric(
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
    db_metric: HealthStatusMetric,
    client_id: str,
    data_import_id: str,
    record: ParsedGarminHealthStatus,
) -> None:
    db_metric.client_id = client_id
    db_metric.data_import_id = data_import_id
    db_metric.source_file = record.source_file
    db_metric.source_record_id = record.source_record_id
    db_metric.calendar_date = record.calendar_date
    db_metric.create_timestamp_utc = record.create_timestamp_utc
    db_metric.update_timestamp_utc = record.update_timestamp_utc
    db_metric.outliers_count = record.outliers_count
    db_metric.heart_rate_value = record.heart_rate_value
    db_metric.heart_rate_status = record.heart_rate_status
    db_metric.heart_rate_baseline_lower = record.heart_rate_baseline_lower
    db_metric.heart_rate_baseline_upper = record.heart_rate_baseline_upper
    db_metric.hrv_value = record.hrv_value
    db_metric.hrv_status = record.hrv_status
    db_metric.hrv_baseline_lower = record.hrv_baseline_lower
    db_metric.hrv_baseline_upper = record.hrv_baseline_upper
    db_metric.respiration_value = record.respiration_value
    db_metric.respiration_status = record.respiration_status
    db_metric.spo2_value = record.spo2_value
    db_metric.spo2_status = record.spo2_status
    db_metric.skin_temp_c_value = record.skin_temp_c_value
    db_metric.skin_temp_c_status = record.skin_temp_c_status
    db_metric.provider_metadata = {
        "metricTypes": list(record.metric_types),
        "outliersCount": record.outliers_count,
    }
