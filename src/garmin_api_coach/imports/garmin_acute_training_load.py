from dataclasses import dataclass
from pathlib import Path
from typing import Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from garmin_api_coach.db.models import AcuteTrainingLoadMetric, Client, DataImport, RawRecord
from garmin_api_coach.providers.garmin.acute_training_load import (
    ParsedGarminAcuteTrainingLoad,
    load_acute_training_load_from_zip,
)
from garmin_api_coach.providers.garmin.summarized_activities import GARMIN_PROVIDER


class GarminAcuteTrainingLoadImportError(ValueError):
    """Raised when Garmin acute training load records cannot be imported."""


@dataclass(frozen=True)
class GarminAcuteTrainingLoadDatabaseImportSummary:
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
    statuses_seen: tuple[str, ...]

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
            "statuses_seen": list(self.statuses_seen),
        }


def import_garmin_acute_training_load(
    db: Session,
    *,
    client_id: str,
    source_path: Union[Path, str],
) -> GarminAcuteTrainingLoadDatabaseImportSummary:
    client = db.get(Client, client_id)
    if client is None:
        raise GarminAcuteTrainingLoadImportError(f"Client does not exist: {client_id}")

    parsed_import = load_acute_training_load_from_zip(source_path)
    source_name = parsed_import.source_path.name

    data_import = DataImport(
        client_id=client.id,
        provider=GARMIN_PROVIDER,
        source_name=source_name,
        source_type="garmin_acute_training_load",
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
        db.add(_raw_record_from_acute_training_load(data_import.id, parsed_record))
        raw_records_created += 1

        existing_metric = db.scalar(
            select(AcuteTrainingLoadMetric).where(
                AcuteTrainingLoadMetric.provider == parsed_record.provider,
                AcuteTrainingLoadMetric.client_id == client.id,
                AcuteTrainingLoadMetric.calendar_date == parsed_record.calendar_date,
            )
        )
        if existing_metric is None:
            db.add(_metric_from_parsed(client.id, data_import.id, parsed_record))
            metrics_inserted += 1
        else:
            _update_metric(existing_metric, client.id, data_import.id, parsed_record)
            metrics_updated += 1

    database_summary = GarminAcuteTrainingLoadDatabaseImportSummary(
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
        statuses_seen=parsed_import.statuses_seen,
    )
    data_import.summary = database_summary.to_summary()
    db.commit()

    return database_summary


def _raw_record_from_acute_training_load(data_import_id: str, record: ParsedGarminAcuteTrainingLoad) -> RawRecord:
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
    record: ParsedGarminAcuteTrainingLoad,
) -> AcuteTrainingLoadMetric:
    db_metric = AcuteTrainingLoadMetric(
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
    db_metric: AcuteTrainingLoadMetric,
    client_id: str,
    data_import_id: str,
    record: ParsedGarminAcuteTrainingLoad,
) -> None:
    db_metric.client_id = client_id
    db_metric.data_import_id = data_import_id
    db_metric.source_file = record.source_file
    db_metric.source_record_id = record.source_record_id
    db_metric.calendar_date = record.calendar_date
    db_metric.timestamp = record.timestamp
    db_metric.acwr_percent = record.acwr_percent
    db_metric.acwr_status = record.acwr_status
    db_metric.acwr_status_feedback = record.acwr_status_feedback
    db_metric.daily_training_load_acute = record.daily_training_load_acute
    db_metric.daily_training_load_chronic = record.daily_training_load_chronic
    db_metric.daily_acute_chronic_workload_ratio = record.daily_acute_chronic_workload_ratio
    db_metric.provider_metadata = {
        "acwrStatus": record.acwr_status,
        "acwrStatusFeedback": record.acwr_status_feedback,
    }
