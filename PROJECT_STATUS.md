# GarminAPICoach Project Status

Date: 2026-05-13

## Current Status

`GarminAPICoach` is a backend-first FastAPI coaching data platform. The current backend can inspect a Garmin export ZIP, parse summarized Garmin activity JSON, import normalized activities, import Garmin training readiness metrics, import Garmin sleep metrics, import Garmin health-status metrics, import Garmin acute training load metrics, expose coach-scoped activity APIs, return deterministic activity analytics, and return a source-attributed readiness summary.

The first real data source is the private Garmin export ZIP in ignored local raw data:

```text
data/raw/642bffa2-69d5-466c-9599-eb82c5e5124b_1.zip
```

The ZIP has been validated locally with:

- 3175 summarized activity records
- 865 Garmin TrainingReadinessDTO records seen
- 864 Garmin TrainingReadinessDTO records parsed
- 280 unique daily training readiness metrics stored after upsert
- 984 Garmin sleep records seen
- 978 Garmin sleep records parsed
- 978 unique daily sleep metrics stored after upsert
- 235 Garmin health-status records seen
- 235 Garmin health-status records parsed
- 235 unique daily health-status metrics stored after upsert
- 2911 Garmin acute training load records seen
- 2911 Garmin acute training load records parsed
- 975 unique daily acute training load metrics stored after upsert

## Built

- FastAPI app and `uv` project setup.
- Settings module with development/test/production environments.
- Local/test auth bypass through a development coach identity.
- SQLAlchemy models and Alembic migration for coaches, clients, data imports, raw records, activity type mappings, and normalized activities.
- Docker Compose Postgres configuration.
- Garmin ZIP structure inspector.
- Garmin summarized activities parser.
- Garmin summarized activities database import service.
- Garmin TrainingReadinessDTO parser.
- Garmin training readiness database import service.
- `training_readiness_metrics` database table and migration.
- Garmin sleep data parser.
- Garmin sleep data database import service.
- `sleep_metrics` database table and migration.
- Garmin health-status data parser.
- Garmin health-status data database import service.
- `health_status_metrics` database table and migration.
- Garmin acute training load parser.
- Garmin acute training load database import service.
- `acute_training_load_metrics` database table and migration.
- Client APIs:
  - `GET /clients`
  - `POST /clients`
- Activity APIs:
  - `GET /activities`
  - `GET /activity-summaries/by-type`
- Analytics API:
  - `GET /analytics/activity-overview`
- Readiness API:
  - `GET /readiness/summary`

## Readiness Behavior

The current readiness endpoint is intentionally conservative.

It uses normalized activities, the latest imported Garmin TrainingReadinessDTO record when available, the latest imported Garmin sleep record when available, the latest imported Garmin health-status record when available, and the latest imported Garmin acute training load record when available.

Current readiness factors:

- `activity_history`
- `running_consistency`
- `training_readiness`
- `acute_training_load`
- `sleep_detail`
- `health_status_detail`
- `recovery_data`
- `data_quality`

Current readiness statuses:

- `green`
- `yellow`
- `red`

With no recovery or load data imported, the overall readiness status will usually be `yellow`. With imported training readiness, acute training load, sleep data, or health-status data, the latest Garmin scores and statuses can move contributing factors to `green`, `yellow`, or `red`.

## Key Files

- `src/garmin_api_coach/main.py`
- `src/garmin_api_coach/settings.py`
- `src/garmin_api_coach/db/models.py`
- `src/garmin_api_coach/providers/garmin/export_inspector.py`
- `src/garmin_api_coach/providers/garmin/summarized_activities.py`
- `src/garmin_api_coach/providers/garmin/training_readiness.py`
- `src/garmin_api_coach/providers/garmin/sleep_data.py`
- `src/garmin_api_coach/providers/garmin/health_status.py`
- `src/garmin_api_coach/providers/garmin/acute_training_load.py`
- `src/garmin_api_coach/imports/garmin_summarized_activities.py`
- `src/garmin_api_coach/imports/garmin_training_readiness.py`
- `src/garmin_api_coach/imports/garmin_sleep_data.py`
- `src/garmin_api_coach/imports/garmin_health_status.py`
- `src/garmin_api_coach/imports/garmin_acute_training_load.py`
- `src/garmin_api_coach/analytics/activity_overview.py`
- `src/garmin_api_coach/analytics/readiness.py`
- `src/garmin_api_coach/api/activities.py`
- `src/garmin_api_coach/api/analytics.py`
- `src/garmin_api_coach/api/readiness.py`
- `tests/test_garmin_training_readiness.py`
- `tests/test_garmin_training_readiness_import_service.py`
- `tests/test_garmin_sleep_data.py`
- `tests/test_garmin_sleep_data_import_service.py`
- `tests/test_garmin_health_status.py`
- `tests/test_garmin_health_status_import_service.py`
- `tests/test_garmin_acute_training_load.py`
- `tests/test_garmin_acute_training_load_import_service.py`
- `tests/test_readiness_api.py`

## Validation

Last validation run:

```bash
uv run pytest
```

Result:

```text
60 passed
```

The first sandboxed test run failed because `uv` could not access `/Users/luisr/.cache/uv` from the restricted sandbox. The tests passed when rerun with approved cache access.

## Constraints

- Do not commit private Garmin exports or athlete data.
- Keep raw Garmin files in ignored `data/raw/`.
- Do not parse FIT files yet.
- Do not add UI, client login, billing, Garmin OAuth, or automatic client messaging yet.
- Keep deterministic analytics as the source of truth. LLM output should explain computed metrics, not replace them.
- Garmin account authorization must stay separate from platform coach login.

## Next Step

Import the next recovery or load-related Garmin JSON source only after checking whether it adds information not already covered by TrainingReadinessDTO, detailed sleep, health-status, and acute training load.

Recommended order:

1. Inspect UDS aggregator shapes in more detail.
2. Choose one small source only if it adds information not already captured by existing normalized tables.
3. Add a normalized recovery/readiness data model only for fields that are actually observed.
4. Extend `GET /readiness/summary` with source-attributed recovery or load factors.
5. Add tests proving missing inputs remain explicit.

Do not add LLM analysis until deterministic readiness has enough recovery and load context to produce stable source-grounded summaries.
