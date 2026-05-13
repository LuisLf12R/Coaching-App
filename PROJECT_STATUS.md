# GarminAPICoach Project Status

Date: 2026-05-13

## Current Status

`GarminAPICoach` is a backend-first FastAPI coaching data platform. The current backend can inspect a Garmin export ZIP, parse summarized Garmin activity JSON, import normalized activities, import Garmin training readiness metrics, import Garmin sleep metrics, import Garmin health-status metrics, import Garmin acute training load metrics, import Garmin UDS daily wellness metrics, expose coach-scoped activity APIs, return deterministic activity analytics, and return a source-attributed readiness summary.

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
- 19 Garmin UDS aggregator files inspected
- 1732 Garmin UDS daily records seen
- 984 Garmin UDS daily records parsed with wellness signals
- 984 unique daily wellness metrics stored after upsert

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
- Garmin UDS daily wellness parser.
- Garmin UDS daily wellness database import service.
- `daily_wellness_metrics` database table and migration.
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

It uses normalized activities, the latest imported Garmin TrainingReadinessDTO record when available, the latest imported Garmin sleep record when available, the latest imported Garmin health-status record when available, the latest imported Garmin acute training load record when available, and the latest imported Garmin UDS daily wellness record when available.

Current readiness factors:

- `activity_history`
- `running_consistency`
- `training_readiness`
- `acute_training_load`
- `sleep_detail`
- `health_status_detail`
- `daily_wellness`
- `recovery_data`
- `data_quality`

Current readiness statuses:

- `green`
- `yellow`
- `red`

With no recovery or load data imported, the overall readiness status will usually be `yellow`. With imported training readiness, acute training load, sleep data, health-status data, or UDS daily wellness data, the latest Garmin scores and statuses can move contributing factors to `green`, `yellow`, or `red`.

The UDS daily wellness importer is intentionally narrow. It normalizes observed daily Body Battery, all-day stress, resting heart rate, steps, respiration, intensity minutes, and Pulse Ox values. It skips older calorie-only UDS records that do not contain useful wellness signals.

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
- `src/garmin_api_coach/providers/garmin/daily_wellness.py`
- `src/garmin_api_coach/imports/garmin_summarized_activities.py`
- `src/garmin_api_coach/imports/garmin_training_readiness.py`
- `src/garmin_api_coach/imports/garmin_sleep_data.py`
- `src/garmin_api_coach/imports/garmin_health_status.py`
- `src/garmin_api_coach/imports/garmin_acute_training_load.py`
- `src/garmin_api_coach/imports/garmin_daily_wellness.py`
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
- `tests/test_garmin_daily_wellness.py`
- `tests/test_garmin_daily_wellness_import_service.py`
- `tests/test_readiness_api.py`

## Validation

Last validation run:

```bash
uv run pytest
```

Result:

```text
68 passed
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

Start the first coach-facing LLM analysis slice only after keeping deterministic readiness as the source of truth.

Recommended order:

1. Define the provider-neutral LLM interface.
2. Build an analysis packet from deterministic activity overview and readiness output.
3. Add a mock LLM provider test before calling a real provider.
4. Store prompt version, model/provider, input window, computed metrics used, output, and timestamp.
5. Keep generated coaching analysis coach-facing only.

Do not let LLM output replace deterministic metrics or readiness factors.
