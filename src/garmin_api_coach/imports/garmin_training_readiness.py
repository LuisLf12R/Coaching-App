from dataclasses import dataclass
from pathlib import Path
from typing import Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from garmin_api_coach.db.models import Client, DataImport, RawRecord, TrainingReadinessMetric
from garmin_api_coach.providers.garmin.summarized_activities import GARMIN_PROVIDER
from garmin_api_coach.providers.garmin.training_readiness import (
    ParsedGarminTrainingReadiness,
    load_training_readiness_from_zip,
)


class GarminTrainingReadinessImportError(ValueError):
    """Raised when Garmin training readiness records cannot be imported."""


@dataclass(frozen=True)
class GarminTrainingReadinessDatabaseImportSummary:
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
    levels_seen: tuple[str, ...]

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
            "levels_seen": list(self.levels_seen),
        }


def import_garmin_training_readiness(
    db: Session,
    *,
    client_id: str,
    source_path: Union[Path, str],
) -> GarminTrainingReadinessDatabaseImportSummary:
    client = db.get(Client, client_id)
    if client is None:
        raise GarminTrainingReadinessImportError(f"Client does not exist: {client_id}")

    parsed_import = load_training_readiness_from_zip(source_path)
    source_name = parsed_import.source_path.name

    data_import = DataImport(
        client_id=client.id,
        provider=GARMIN_PROVIDER,
        source_name=source_name,
        source_type="garmin_training_readiness",
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
        db.add(_raw_record_from_readiness(data_import.id, parsed_record))
        raw_records_created += 1

        existing_metric = db.scalar(
            select(TrainingReadinessMetric).where(
                TrainingReadinessMetric.provider == parsed_record.provider,
                TrainingReadinessMetric.client_id == client.id,
                TrainingReadinessMetric.calendar_date == parsed_record.calendar_date,
            )
        )
        if existing_metric is None:
            db.add(_metric_from_parsed(client.id, data_import.id, parsed_record))
            metrics_inserted += 1
        else:
            _update_metric(existing_metric, client.id, data_import.id, parsed_record)
            metrics_updated += 1

    database_summary = GarminTrainingReadinessDatabaseImportSummary(
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
        levels_seen=parsed_import.levels_seen,
    )
    data_import.summary = database_summary.to_summary()
    db.commit()

    return database_summary


def _raw_record_from_readiness(data_import_id: str, record: ParsedGarminTrainingReadiness) -> RawRecord:
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
    record: ParsedGarminTrainingReadiness,
) -> TrainingReadinessMetric:
    db_metric = TrainingReadinessMetric(
        client_id=client_id,
        data_import_id=data_import_id,
        provider=record.provider,
        source_file=record.source_file,
        source_record_id=record.source_record_id,
        calendar_date=record.calendar_date,
        level=record.level,
        score=record.score,
    )
    _update_metric(db_metric, client_id, data_import_id, record)
    return db_metric


def _update_metric(
    db_metric: TrainingReadinessMetric,
    client_id: str,
    data_import_id: str,
    record: ParsedGarminTrainingReadiness,
) -> None:
    db_metric.client_id = client_id
    db_metric.data_import_id = data_import_id
    db_metric.source_file = record.source_file
    db_metric.source_record_id = record.source_record_id
    db_metric.calendar_date = record.calendar_date
    db_metric.timestamp = record.timestamp
    db_metric.timestamp_local = record.timestamp_local
    db_metric.level = record.level
    db_metric.score = record.score
    db_metric.feedback_short = record.feedback_short
    db_metric.feedback_long = record.feedback_long
    db_metric.sleep_score = record.sleep_score
    db_metric.sleep_score_factor_percent = record.sleep_score_factor_percent
    db_metric.recovery_time = record.recovery_time
    db_metric.recovery_time_factor_percent = record.recovery_time_factor_percent
    db_metric.acwr_factor_percent = record.acwr_factor_percent
    db_metric.stress_history_factor_percent = record.stress_history_factor_percent
    db_metric.hrv_factor_percent = record.hrv_factor_percent
    db_metric.sleep_history_factor_percent = record.sleep_history_factor_percent
    db_metric.valid_sleep = record.valid_sleep
    db_metric.input_context = record.input_context
    db_metric.hrv_weekly_average = record.hrv_weekly_average
    db_metric.acute_load = record.acute_load
    db_metric.provider_metadata = {
        "feedbackShort": record.feedback_short,
        "feedbackLong": record.feedback_long,
        "inputContext": record.input_context,
    }
