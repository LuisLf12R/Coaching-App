# GarminAPICoach Project Status

Date: 2026-05-13

## Current Status

`GarminAPICoach` is a backend-first FastAPI coaching data platform. The current backend can inspect a Garmin export ZIP, parse summarized Garmin activity JSON, import normalized activities, import Garmin training readiness metrics, expose coach-scoped activity APIs, return deterministic activity analytics, and return a source-attributed readiness summary.

The first real data source is the private Garmin export ZIP in ignored local raw data:

```text
data/raw/642bffa2-69d5-466c-9599-eb82c5e5124b_1.zip
```

The ZIP has been validated locally with:

- 3175 summarized activity records
- 865 Garmin TrainingReadinessDTO records seen
- 864 Garmin TrainingReadinessDTO records parsed
- 280 unique daily training readiness metrics stored after upsert

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

It uses normalized activities and the latest imported Garmin TrainingReadinessDTO record when available. It does not infer detailed sleep or health-status data until those source files are imported.

Current readiness factors:

- `activity_history`
- `running_consistency`
- `training_readiness`
- `recovery_data`
- `data_quality`

Current readiness statuses:

- `green`
- `yellow`
- `red`

With no training readiness data imported, the overall readiness status will usually be `yellow`. With imported training readiness, the latest Garmin score and level can move the overall status to `green`, `yellow`, or `red`.

## Key Files

- `src/garmin_api_coach/main.py`
- `src/garmin_api_coach/settings.py`
- `src/garmin_api_coach/db/models.py`
- `src/garmin_api_coach/providers/garmin/export_inspector.py`
- `src/garmin_api_coach/providers/garmin/summarized_activities.py`
- `src/garmin_api_coach/providers/garmin/training_readiness.py`
- `src/garmin_api_coach/imports/garmin_summarized_activities.py`
- `src/garmin_api_coach/imports/garmin_training_readiness.py`
- `src/garmin_api_coach/analytics/activity_overview.py`
- `src/garmin_api_coach/analytics/readiness.py`
- `src/garmin_api_coach/api/activities.py`
- `src/garmin_api_coach/api/analytics.py`
- `src/garmin_api_coach/api/readiness.py`
- `tests/test_garmin_training_readiness.py`
- `tests/test_garmin_training_readiness_import_service.py`
- `tests/test_readiness_api.py`

## Validation

Last validation run:

```bash
uv run pytest
```

Result:

```text
36 passed
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

Import the next detailed recovery-related Garmin JSON source and wire it into readiness with source attribution.

Recommended order:

1. Inspect the local Garmin export files for sleep, health status, acute training load, and UDS aggregator shapes.
2. Choose one small source to import next, likely sleep data or health status.
3. Add a normalized recovery/readiness data model only for fields that are actually observed.
4. Extend `GET /readiness/summary` with source-attributed recovery factors.
5. Add tests proving missing inputs remain explicit.

Do not add LLM analysis until deterministic readiness has at least one detailed recovery input beyond Garmin's aggregate training readiness score.
