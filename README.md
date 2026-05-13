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

Run the API locally:

```bash
uv run uvicorn garmin_api_coach.main:app --reload
```

Health check:

```text
GET /health
```
