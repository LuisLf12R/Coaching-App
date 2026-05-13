from dataclasses import dataclass
from pathlib import Path
from typing import Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from garmin_api_coach.db.models import Client, DataImport, RawRecord, SleepMetric
from garmin_api_coach.providers.garmin.sleep_data import ParsedGarminSleepMetric, load_sleep_data_from_zip
from garmin_api_coach.providers.garmin.summarized_activities import GARMIN_PROVIDER


class GarminSleepDataImportError(ValueError):
    """Raised when Garmin sleep records cannot be imported."""


@dataclass(frozen=True)
class GarminSleepDatabaseImportSummary:
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


def import_garmin_sleep_data(
    db: Session,
    *,
    client_id: str,
    source_path: Union[Path, str],
) -> GarminSleepDatabaseImportSummary:
    client = db.get(Client, client_id)
    if client is None:
        raise GarminSleepDataImportError(f"Client does not exist: {client_id}")

    parsed_import = load_sleep_data_from_zip(source_path)
    source_name = parsed_import.source_path.name

    data_import = DataImport(
        client_id=client.id,
        provider=GARMIN_PROVIDER,
        source_name=source_name,
        source_type="garmin_sleep_data",
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
        db.add(_raw_record_from_sleep(data_import.id, parsed_record))
        raw_records_created += 1

        existing_metric = db.scalar(
            select(SleepMetric).where(
                SleepMetric.provider == parsed_record.provider,
                SleepMetric.client_id == client.id,
                SleepMetric.calendar_date == parsed_record.calendar_date,
            )
        )
        if existing_metric is None:
            db.add(_metric_from_parsed(client.id, data_import.id, parsed_record))
            metrics_inserted += 1
        else:
            _update_metric(existing_metric, client.id, data_import.id, parsed_record)
            metrics_updated += 1

    database_summary = GarminSleepDatabaseImportSummary(
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


def _raw_record_from_sleep(data_import_id: str, record: ParsedGarminSleepMetric) -> RawRecord:
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
    record: ParsedGarminSleepMetric,
) -> SleepMetric:
    db_metric = SleepMetric(
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
    db_metric: SleepMetric,
    client_id: str,
    data_import_id: str,
    record: ParsedGarminSleepMetric,
) -> None:
    db_metric.client_id = client_id
    db_metric.data_import_id = data_import_id
    db_metric.source_file = record.source_file
    db_metric.source_record_id = record.source_record_id
    db_metric.calendar_date = record.calendar_date
    db_metric.sleep_start_gmt = record.sleep_start_gmt
    db_metric.sleep_end_gmt = record.sleep_end_gmt
    db_metric.deep_sleep_seconds = record.deep_sleep_seconds
    db_metric.light_sleep_seconds = record.light_sleep_seconds
    db_metric.rem_sleep_seconds = record.rem_sleep_seconds
    db_metric.awake_sleep_seconds = record.awake_sleep_seconds
    db_metric.unmeasurable_seconds = record.unmeasurable_seconds
    db_metric.awake_count = record.awake_count
    db_metric.restless_moment_count = record.restless_moment_count
    db_metric.avg_sleep_stress = record.avg_sleep_stress
    db_metric.average_respiration = record.average_respiration
    db_metric.lowest_respiration = record.lowest_respiration
    db_metric.highest_respiration = record.highest_respiration
    db_metric.overall_score = record.overall_score
    db_metric.quality_score = record.quality_score
    db_metric.duration_score = record.duration_score
    db_metric.recovery_score = record.recovery_score
    db_metric.restfulness_score = record.restfulness_score
    db_metric.feedback = record.feedback
    db_metric.insight = record.insight
    db_metric.provider_metadata = {
        "feedback": record.feedback,
        "insight": record.insight,
    }
