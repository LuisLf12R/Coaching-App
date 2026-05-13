# GarminAPICoach

Backend-first coaching data platform for Garmin and future data providers.

## First Local Commands

Install dependencies:

```bash
uv sync
```

Run tests:

```bash
uv run pytest
```

Start local Postgres:

```bash
docker compose up -d
```

Run database migrations:

```bash
uv run alembic upgrade head
```

Run the API locally:

```bash
uv run uvicorn garmin_api_coach.main:app --reload
```

Health check:

```text
GET /health
```

Current coach-side endpoints include:

```text
GET /clients
POST /clients
GET /activities
GET /activity-summaries/by-type
GET /analytics/activity-overview
GET /readiness/summary
```

## Local Raw Data

Keep sensitive source exports in:

```text
data/raw/
```

That folder is ignored by Git. Do not commit Garmin export ZIPs or athlete data.
