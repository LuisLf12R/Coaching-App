from garmin_api_coach.db.base import Base
from garmin_api_coach.db import models  # noqa: F401
from garmin_api_coach.settings import Settings


def test_default_database_url_names_local_dev_database() -> None:
    settings = Settings()

    assert "garmin_api_coach_dev" in settings.database_url


def test_initial_database_models_are_registered() -> None:
    expected_tables = {
        "coaches",
        "clients",
        "data_imports",
        "raw_records",
        "activity_type_mappings",
        "activities",
        "training_readiness_metrics",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_activities_keep_provider_metadata_for_later_mapping() -> None:
    activity_columns = Base.metadata.tables["activities"].columns

    assert "provider_metadata" in activity_columns
