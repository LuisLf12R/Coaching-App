from dataclasses import dataclass
from pathlib import Path
from typing import Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from garmin_api_coach.db.models import Activity, Client, DataImport, RawRecord
from garmin_api_coach.providers.garmin.summarized_activities import (
    GARMIN_PROVIDER,
    ParsedGarminSummarizedActivity,
    load_summarized_activities_from_zip,
)


class GarminActivityImportError(ValueError):
    """Raised when Garmin summarized activities cannot be imported."""


@dataclass(frozen=True)
class GarminActivityDatabaseImportSummary:
    data_import_id: str
    client_id: str
    source_path: Path
    source_name: str
    parser_version: str
    records_seen: int
    records_parsed: int
    records_invalid: int
    raw_records_created: int
    activities_inserted: int
    activities_updated: int
    unknown_activity_types: tuple[str, ...]
    unknown_sport_types: tuple[str, ...]

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
            "activities_inserted": self.activities_inserted,
            "activities_updated": self.activities_updated,
            "unknown_activity_types": list(self.unknown_activity_types),
            "unknown_sport_types": list(self.unknown_sport_types),
        }


def import_garmin_summarized_activities(
    db: Session,
    *,
    client_id: str,
    source_path: Union[Path, str],
) -> GarminActivityDatabaseImportSummary:
    client = db.get(Client, client_id)
    if client is None:
        raise GarminActivityImportError(f"Client does not exist: {client_id}")

    parsed_import = load_summarized_activities_from_zip(source_path)
    source_name = parsed_import.source_path.name

    data_import = DataImport(
        client_id=client.id,
        provider=GARMIN_PROVIDER,
        source_name=source_name,
        source_type="garmin_export_zip",
        parser_version=parsed_import.parser_version,
        status="completed" if parsed_import.records_invalid == 0 else "completed_with_warnings",
        summary=parsed_import.to_summary(),
    )
    db.add(data_import)
    db.flush()

    raw_records_created = 0
    activities_inserted = 0
    activities_updated = 0

    for parsed_activity in parsed_import.activities:
        db.add(_raw_record_from_activity(data_import.id, parsed_activity))
        raw_records_created += 1

        existing_activity = db.scalar(
            select(Activity).where(
                Activity.provider == parsed_activity.provider,
                Activity.source_activity_id == parsed_activity.source_activity_id,
            )
        )
        if existing_activity is None:
            db.add(_activity_from_parsed(client.id, data_import.id, parsed_activity))
            activities_inserted += 1
        else:
            _update_activity(existing_activity, client.id, data_import.id, parsed_activity)
            activities_updated += 1

    database_summary = GarminActivityDatabaseImportSummary(
        data_import_id=data_import.id,
        client_id=client.id,
        source_path=parsed_import.source_path,
        source_name=source_name,
        parser_version=parsed_import.parser_version,
        records_seen=parsed_import.records_seen,
        records_parsed=parsed_import.records_parsed,
        records_invalid=parsed_import.records_invalid,
        raw_records_created=raw_records_created,
        activities_inserted=activities_inserted,
        activities_updated=activities_updated,
        unknown_activity_types=parsed_import.unknown_activity_types,
        unknown_sport_types=parsed_import.unknown_sport_types,
    )
    data_import.summary = database_summary.to_summary()
    db.commit()

    return database_summary


def _raw_record_from_activity(data_import_id: str, activity: ParsedGarminSummarizedActivity) -> RawRecord:
    return RawRecord(
        data_import_id=data_import_id,
        provider=activity.provider,
        source_name=activity.source_file,
        source_record_id=activity.source_activity_id,
        parser_version=activity.parser_version,
        validation_status="valid",
        payload=activity.raw_payload,
    )


def _activity_from_parsed(
    client_id: str,
    data_import_id: str,
    activity: ParsedGarminSummarizedActivity,
) -> Activity:
    db_activity = Activity(
        client_id=client_id,
        data_import_id=data_import_id,
        provider=activity.provider,
        source_activity_id=activity.source_activity_id,
    )
    _update_activity(db_activity, client_id, data_import_id, activity)
    return db_activity


def _update_activity(
    db_activity: Activity,
    client_id: str,
    data_import_id: str,
    activity: ParsedGarminSummarizedActivity,
) -> None:
    db_activity.client_id = client_id
    db_activity.data_import_id = data_import_id
    db_activity.source_file = activity.source_file
    db_activity.activity_type = activity.activity_type
    db_activity.sport_type = activity.sport_type
    db_activity.start_time_gmt = activity.start_time_gmt
    db_activity.start_time_local = activity.start_time_local
    db_activity.duration_seconds = activity.duration_seconds
    db_activity.distance_meters = activity.distance_meters
    db_activity.avg_speed_meters_per_second = activity.avg_speed_meters_per_second
    db_activity.avg_hr = activity.avg_hr
    db_activity.max_hr = activity.max_hr
    db_activity.calories = activity.calories
    db_activity.steps = activity.steps
    db_activity.training_effect_label = activity.training_effect_label
    db_activity.activity_training_load = activity.activity_training_load
    db_activity.provider_metadata = activity.provider_metadata
