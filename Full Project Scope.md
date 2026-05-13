# Full Project Scope

Date: 2026-05-13

## Product Direction

Build a backend-first coaching data platform that starts with Luis coaching friends, then grows into a full product that can support more coaches, more athletes, more sports, more data providers, and multiple LLM providers.

The first version is coach-side only. Client login, client-facing dashboards, payments, and workout delivery come later.

The platform should be modular from the beginning. Garmin and running are the first use case, not permanent assumptions.

Internal project name:

```text
GarminAPICoach
```

## Core Product Goal

Give a coach a reliable system to ingest athlete data, normalize it, analyze it, and generate coach-facing insights that support better training decisions.

The system should help the coach answer:

- What has the athlete been doing?
- How is the athlete recovering?
- What changed recently?
- What risks or anomalies deserve attention?
- What should the coach consider adjusting?
- What data supports that conclusion?

The LLM is a coach assistant, not the source of truth and not an automatic client communicator.

## First User

Luis is the first coach user.

Initial athletes are Luis and consenting friends. Luis's Garmin data is the first real data source. Friend data can be added later to test additional sports and data shapes.

## First Data Source

Initial preliminary downloaded file:

```text
/Users/luisr/Downloads/Activities.csv
```

For project use, copy source files into a project raw-data folder instead of depending on files in Downloads. This CSV is preliminary and should now be treated as a fallback or simple validation fixture, not the primary source for the first real importer.

Current observed structure:

```text
Month, Activity Type, Value
Jun 2025, Running, 25
Jun 2025, Cycling, 1
Jun 2025, Gym & Fitness Equipment, 28
```

This file is useful for early ingestion validation, provider parsing, activity classification, and monthly activity-count summaries.

It is not enough for deeper coaching analytics because it does not include:

- individual activity records
- duration
- distance
- pace or speed
- heart rate
- elevation
- training effect
- sleep
- HRV
- stress
- Body Battery
- daily health metrics

To build the stronger backend, the data model may still support this CSV later, but the first real Garmin ingestion path should now target the delivered Garmin export ZIP.

Luis received a full Garmin data export from Garmin's export flow on 2026-05-12.

Delivered export file:

```text
/Users/luisr/Documents/All docs/Garmin App/642bffa2-69d5-466c-9599-eb82c5e5124b_1.zip
```

Observed full export shape:

- a ZIP archive
- 163 MB outer ZIP
- 193 outer entries
- 151 JSON files
- 7 nested ZIP files
- 3 PNG files
- `DI_CONNECT/` as the primary project-relevant folder
- original uploaded activity files mostly as FIT files inside nested ZIPs

Important observed folders:

- `DI_CONNECT/DI-Connect-Fitness/`
- `DI_CONNECT/DI-Connect-Wellness/`
- `DI_CONNECT/DI-Connect-Metrics/`
- `DI_CONNECT/DI-Connect-Aggregator/`
- `DI_CONNECT/DI-Connect-Uploaded-Files/`
- `DI_CONNECT/DI-Connect-Device/`
- `DI_CONNECT/DI-Connect-User/`

Most important first ingestion source:

```text
DI_CONNECT/DI-Connect-Fitness/*_summarizedActivities.json
```

Observed summarized activity files:

```text
luisrivglez@gmail.com_0_summarizedActivities.json      1000 activities
luisrivglez@gmail.com_1001_summarizedActivities.json   1000 activities
luisrivglez@gmail.com_2002_summarizedActivities.json   1000 activities
luisrivglez@gmail.com_3003_summarizedActivities.json    175 activities
```

Total observed summarized activity records:

```text
3175
```

Useful activity fields observed:

- `activityId`
- `activityType`
- `sportType`
- `startTimeGmt`
- `startTimeLocal`
- `duration`
- `distance`
- `avgSpeed`
- `avgHr`
- `maxHr`
- `calories`
- `steps`
- `trainingEffectLabel`
- `activityTrainingLoad`

Nested uploaded activity file ZIPs:

```text
DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_0-_Part1.zip
DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_0-_Part2.zip
DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_0-_Part3.zip
DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_0-_Part4.zip
```

Observed nested uploaded activity files:

```text
18597 FIT files
```

These FIT files are valuable for detailed later parsing, but they should not be the first importer because the summarized activity JSON already provides structured activity-level records.

Useful wellness and metrics sources observed:

- `DI_CONNECT/DI-Connect-Wellness/*_sleepData.json`
- `DI_CONNECT/DI-Connect-Wellness/*_healthStatusData.json`
- `DI_CONNECT/DI-Connect-Aggregator/UDSFile_*.json`
- `DI_CONNECT/DI-Connect-Metrics/TrainingReadinessDTO_*.json`
- `DI_CONNECT/DI-Connect-Metrics/MetricsAcuteTrainingLoad_*.json`
- `DI_CONNECT/DI-Connect-Metrics/TrainingHistory_*.json`

The ingestion system should inspect ZIP structure before assuming a fixed schema. The first structure-discovery pass has been completed manually, but the product should still include a reusable ZIP inspection/import summary step.

## Scope Decision

Build Scope C first: a coaching platform backend.

Do not start with UI/UX. The first priority is a strong backend foundation:

- data contracts
- database schema
- ingestion
- normalization
- analytics
- readiness logic
- coach-facing AI analysis
- API endpoints
- validation and tests

## Main Design Principle

The platform should be modular and replaceable.

Modules should be swappable without rewriting the whole system:

- data provider: Garmin, Polar, Oura, Whoop, manual CSV, future providers
- primary sport: running, cycling, triathlon, strength, swimming, mixed endurance
- LLM provider: OpenAI, local Ollama, Anthropic, future providers
- database: Postgres first, compatible with future production hosting
- analysis engine: deterministic metrics first, AI explanation second
- frontend: future UI can consume stable API endpoints

## Recommended Technical Foundation

Use this stack from the start:

- Backend: FastAPI
- Database: Postgres
- Dependency and environment management: `uv`
- ORM and migrations: SQLAlchemy plus Alembic, unless a better project-specific choice is made later
- Data validation: Pydantic
- Ingestion jobs: plain Python modules called from CLI or background jobs
- API docs: FastAPI OpenAPI
- Testing: pytest
- LLM integration: provider adapter interface
- Secrets: environment variables, never hardcoded

FastAPI should expose API endpoints from day one, but ingestion and analytics should live in plain Python modules so they can be tested without running the web server.

Use a deployment-friendly local setup. Prefer Docker Compose for local Postgres so the project can be reproduced on another machine and later deployed without depending on a specific local database installation.

The first implementation should live inside:

```text
Garmin App/
```

The folder can be renamed later if the product name changes.

Use `uv` rather than Poetry or plain `pip` for the first implementation. It gives the project a reproducible modern Python workflow with less project overhead than Poetry and stronger dependency locking than a simple `requirements.txt`.

## System Architecture

```text
Provider files / APIs
  -> Provider adapter
  -> Raw data store
  -> Normalization layer
  -> Postgres application database
  -> Analytics engine
  -> Readiness engine
  -> LLM analysis adapter
  -> Coach API endpoints
  -> Future frontend
```

## Core Modules

### 1. Provider Adapters

Purpose: accept data from different external sources without tying the platform to one provider.

Initial adapters:

- Garmin CSV adapter for the current `Activities.csv`
- Garmin richer export adapter later
- Garmin official API adapter later

Future adapters:

- Polar
- Oura
- Whoop
- manual uploads

Each adapter should output internal normalized objects, not provider-specific objects.

### 2. Raw Data Store

Purpose: preserve original imported data for traceability.

Store:

- provider name
- source file name or API event ID
- import timestamp
- athlete/client mapping
- raw payload or file reference
- parser version
- validation status

Raw data should not be overwritten. If data is re-imported, create a new import record or explicit replacement policy.

### 3. Client and Coach Domain

Initial coach-side model:

- coach
- client/athlete
- sport focus
- goals
- injury notes
- training constraints
- coach notes
- data provider accounts

No client login in the first version, but the schema should not block future client accounts.

### 4. Activity Domain

Activities should support multiple sports.

Initial sport handling:

- running as the first primary analysis focus
- cycling stored and summarized
- strength/gym stored and summarized
- walking stored and summarized
- unknown activity types preserved and mapped later

Activity model should eventually support:

- activity type
- start time
- duration
- distance
- pace or speed
- average heart rate
- max heart rate
- calories
- elevation
- training effect
- source provider
- source activity ID
- file references for FIT, TCX, or GPX

The current CSV only supports monthly counts, so it should be ingested into an aggregate activity-count table, not forced into fake individual activities.

### 5. Health Metrics Domain

Design for Garmin health data even if the first file does not contain it.

Daily health model should support:

- date
- resting heart rate
- average heart rate
- HRV
- sleep duration
- sleep score
- stress
- Body Battery
- steps
- calories
- respiration
- Pulse Ox
- provider source

This enables future Garmin Health API, Oura, Whoop, and Polar integrations.

### 6. Analytics Engine

Deterministic analytics come before AI.

Initial analytics:

- monthly activity counts by sport
- running frequency trend
- strength frequency trend
- sport mix
- missing-data warnings

Running-focused future analytics:

- weekly running volume
- distance trend
- pace trend
- intensity distribution
- long-run progression
- acute workload spike
- easy/hard session balance
- training consistency

Recovery future analytics:

- sleep trend
- resting HR trend
- HRV trend
- stress trend
- Body Battery trend
- recovery risk factors

### 7. Readiness Engine

Externally expose simple statuses:

- green: ready
- yellow: caution
- red: reduce load

Internally calculate readiness from separate signals:

- training load
- workload spike
- sleep trend
- HRV trend
- resting HR trend
- stress trend
- Body Battery trend
- recent activity intensity
- injury notes
- subjective check-ins later

The color is a summary, not the full model.

For the current CSV, readiness should not pretend to know recovery. It can only produce limited activity-consistency signals and missing-data warnings.

### 8. LLM Analysis

AI should be coach-facing only in the first version.

The LLM should receive a compact analysis packet containing computed metrics, not raw unfiltered data.

Initial output should include:

- coach summary
- notable trends
- risks or uncertainty
- recommended coaching considerations
- questions to ask the athlete
- optional message draft clearly marked as draft

Store:

- prompt version
- model/provider
- input data window
- computed metrics used
- generated output
- timestamp
- coach approval status, added later

LLM providers should use an adapter so the system can switch between OpenAI, Ollama, or another provider.

First development LLM provider:

- local Ollama using `phi4:14b-fp16` as the first default model

Ollama is for development and testing only at first. The production system should support configurable LLM providers by coach or deployment, including Anthropic, Google, OpenAI, and local models.

The Ollama integration should be implemented through the same provider interface that future cloud or local LLM integrations will use.

First production LLM provider:

- OpenAI

The production LLM interface should still remain provider-neutral so Anthropic, Google, or local models can be added later per coach or deployment.

## API-First Backend

FastAPI endpoints should be designed for a future UI.

Initial endpoint groups:

- `/health`: system health check
- `/clients`: create/list/update coach-managed clients
- `/providers`: list supported providers and import statuses
- `/imports`: upload or register source data
- `/activities`: query normalized activity data
- `/activity-aggregates`: query monthly counts and sport mix
- `/analytics`: query deterministic metrics
- `/readiness`: query readiness summaries and underlying factors
- `/ai-analysis`: generate and retrieve coach-facing AI summaries

Use the final auth pipeline shape from the start, but keep it testable through a local development bypass.

Auth direction:

- model coach ownership from day one
- protect API routes through an auth dependency
- support a local test bypass that injects a development coach identity
- keep the bypass isolated to local/test settings
- target OAuth-style authentication for production
- support future Google OAuth for coach login
- keep Garmin account authorization separate from coach login
- do not build full client login yet
- avoid hardcoding user identity inside business logic

This lets the backend grow into real authentication later without rewriting endpoint ownership and permissions.

Important distinction:

- Coach login auth controls access to this platform.
- Garmin account authorization controls permission to access an athlete's Garmin data.

These should be separate flows even if both use OAuth-style authorization.

Recommended auth path:

- build the backend around provider-neutral OIDC/JWT claims
- use a local/test auth bypass during early backend development
- evaluate Clerk first when adding real coach login and the first frontend
- keep Auth0 as the fallback if FastAPI-first API authorization or enterprise identity becomes more important
- avoid direct Google OAuth as the main auth system unless the product stays very simple

Current local/test auth implementation decision:

- The development coach identity uses a plain string email field instead of Pydantic `EmailStr`.
- Reason: `EmailStr` requires the optional `email-validator` dependency, and the current `/me` endpoint is only proving the local/test auth dependency shape.
- Future step: add explicit email validation when real coach accounts, persisted users, Clerk/Auth0 claims, or invite flows are implemented.
- Do not add `email-validator` only for the temporary local bypass unless another validated email surface needs it.

Auth provider options:

- Clerk: best first evaluation for a future SaaS-style coaching product because it has strong React support, prebuilt auth UI, organizations, invitations, roles, and B2B features.
- Auth0: strongest FastAPI/API-first fit and mature enterprise identity option, but heavier for an early product.
- Supabase Auth: strong if the project also commits to Supabase as the hosted Postgres/backend platform, less compelling if the app keeps its own Postgres and FastAPI backend.
- Google OAuth directly: simplest sign-in provider, but too much custom work for roles, organizations, invitations, and future coach/client access rules.
- Google Cloud Identity Platform or Firebase Auth: scalable Google-managed option, useful if the product moves heavily into Google Cloud, but not the simplest first path.

## Database Direction

Use Postgres from the beginning.

Initial tables should likely include:

- coaches
- clients
- provider_accounts
- data_imports
- raw_records
- activity_type_mappings
- activity_count_aggregates
- activities
- daily_health_metrics
- analytics_runs
- readiness_scores
- llm_analysis_runs

The first implementation can start with a smaller subset:

- clients
- data_imports
- raw_records
- activity_type_mappings
- activity_count_aggregates

Then add richer activity and health tables when richer data is available.

## Development Phases

### Phase 1: Backend Skeleton

Goal: create the product-shaped backend foundation.

Build:

- FastAPI app
- Postgres connection
- migrations
- base models
- auth dependency with local/test bypass
- health endpoint
- test setup
- project configuration

Validation:

- app starts
- database migration runs
- health endpoint returns OK
- tests pass

### Phase 2: First Data Ingestion

Goal: ingest Luis's Garmin export summarized activity JSON into normalized activity records without parsing detailed FIT files yet.

Build:

- Garmin export ZIP inspector
- Garmin summarized activities JSON provider adapter
- summarized activities schema validation
- raw import record
- activity type mapping
- normalized activity storage
- source file references for later FIT linking
- import summary with row counts

Validation:

- detects the Garmin export ZIP structure
- finds 4 summarized activity JSON files
- imports 3175 summarized activity records
- preserves source activity IDs
- recognizes observed Garmin activity and sport types
- stores raw import metadata
- reports unsupported or unknown types clearly

### Phase 3: API Around Imported Data

Goal: expose imported data for future UI.

Build:

- list clients
- create a client
- attach import to a client
- list normalized activities
- list activity summaries by type and sport
- summarize sport mix by month or week
- summarize running frequency and basic volume where distance exists

Validation:

- API tests for client creation
- API tests for import query
- API tests for activity query and activity summary responses

### Phase 4: Analytics Engine

Goal: produce deterministic coach-useful insights from available data.

Build:

- activity consistency metrics
- sport mix metrics
- running frequency trend
- running duration and distance trend where available
- strength frequency trend
- missing-data warnings

Validation:

- test metrics against known summarized activity records
- verify the system flags missing or incomplete fields correctly

### Phase 5: Readiness Foundation

Goal: create the readiness engine structure using available Garmin readiness, sleep, health, wellness, and load JSON without pretending FIT-level detail has been parsed.

Build:

- readiness factor model
- readiness status output
- missing recovery-data warnings
- placeholder-free scoring, no fake health inference
- Garmin readiness source mapping

Validation:

- readiness output identifies which Garmin source files contributed each factor
- missing sleep/HRV/stress/load data is explicit when unavailable
- no false precision

### Phase 6: Coach-Facing LLM Analysis

Goal: generate coach-only analysis from deterministic metrics.

Build:

- LLM provider interface
- analysis packet builder
- prompt versioning
- JSON output schema
- storage of model, prompt version, inputs, output, and timestamp

Validation:

- mock LLM test
- output schema validation
- stored analysis can be retrieved

### Phase 7: Rich Garmin Data

Goal: add detailed FIT parsing after the summarized JSON ingestion path is stable.

Possible sources:

- FIT files
- TCX/GPX files
- official Garmin APIs after approval

Build:

- richer activity ingestion
- daily health ingestion
- running analytics
- recovery analytics
- richer readiness factors

### Phase 8: Future Product Layers

Later additions:

- authentication
- coach account management
- client login
- consent flows
- dashboard UI
- client-facing summaries
- recommendation approval workflow
- workout planning
- Garmin Training API workout push
- billing
- organization/team support

## What Not To Build Yet

Do not build these in the first backend milestone:

- polished UI
- client login
- billing
- multi-coach organizations
- Garmin OAuth
- workout push
- complex training plan builder
- automatic client messaging
- medical claims

## Privacy and Safety Requirements

Treat all athlete health and training data as sensitive.

Minimum rules:

- explicit consent before importing friend/client data
- no Garmin passwords or credentials stored
- secrets only in environment variables
- raw data preserved and traceable
- clear deletion path later
- LLM outputs stored with source metrics and prompt version
- coach reviews recommendations before any client-facing use
- recommendations are coaching support, not medical advice

## Immediate Next Build Milestone

Build the backend skeleton and first Garmin ZIP summarized-activity ingestion path.

Concrete milestone:

1. Initial FastAPI/`uv` scaffold accepted as the first checkpoint.
2. Config module and local/test auth dependency created after Luis approved the shape.
3. Configure Postgres through Docker Compose after confirming Docker availability.
4. Create SQLAlchemy and Alembic setup.
5. Define initial models for coaches, clients, data imports, raw records, activity type mappings, and normalized activities.
6. Add project raw-data guidance for storing the Garmin export ZIP without committing sensitive source data.
7. Build Garmin export ZIP inspector.
8. Build Garmin summarized activities JSON adapter.
9. Import the 3175 summarized activity records for one initial client.
10. Expose API endpoints to query normalized activities and activity summaries.
11. Add tests for parsing, validation, import summaries, and API responses.

This milestone proves the backend architecture and modular ingestion path before parsing FIT files, adding richer readiness logic, or building UI.

## Open Questions

1. Should the raw Garmin export ZIP live inside the project folder as a local ignored file, or should the project reference an external raw-data location?
2. Should OpenAI be configured globally for the platform first, or should the schema support per-coach LLM provider settings from the beginning?
3. Should the first normalized activity table store only stable fields from summarized activities, or include a JSON metadata column for extra Garmin-specific fields?

## Handoff

Current status:

- The product direction is a backend-first coaching data platform.
- The first user is Luis acting as coach.
- The first implementation lives inside `Garmin App/`.
- The internal project name is `GarminAPICoach`.
- `uv` has been installed locally through Homebrew.
- The project is now connected to GitHub:
  - repository: `https://github.com/LuisLf12R/Coaching-App.git`
  - branch: `main`
  - initial commit pushed: `e6651ad Initial backend scaffold`
  - latest commit pushed: `fc35e0c Add auth and database foundation`
- Initial backend scaffold has been created:
  - `pyproject.toml`
  - `README.md`
  - `.gitignore`
  - `src/garmin_api_coach/main.py`
  - `src/garmin_api_coach/api/health.py`
  - `tests/test_health.py`
- Config and local/test auth foundation has been created:
  - `src/garmin_api_coach/settings.py`
  - `src/garmin_api_coach/auth/__init__.py`
  - `src/garmin_api_coach/auth/schemas.py`
  - `src/garmin_api_coach/auth/dependencies.py`
  - `src/garmin_api_coach/api/me.py`
  - `tests/test_settings.py`
  - `tests/test_auth.py`
- Health endpoint validation passed with `uv run pytest`.
- Local server validation passed with `GET /health`.
- Current test validation passed with `uv run pytest`: 11 tests passing.
- Cleanliness validation passed:
  - `git diff --check`
  - `uv run pytest`
  - `uv run alembic upgrade head --sql`
- Local Postgres has been configured through Docker Compose:
  - `docker-compose.yml`
  - database: `garmin_api_coach_dev`
  - user: `garmin_api_coach`
  - local port: `5432`
- SQLAlchemy and Alembic foundation has been created:
  - `src/garmin_api_coach/db/base.py`
  - `src/garmin_api_coach/db/session.py`
  - `src/garmin_api_coach/db/models.py`
  - `alembic.ini`
  - `alembic/env.py`
  - `alembic/versions/20260513_0001_initial_schema.py`
- Initial database models have been created:
  - coaches
  - clients
  - data_imports
  - raw_records
  - activity_type_mappings
  - activities
- Local raw Garmin exports should live in ignored `data/raw/`.
- Docker was not available in the current shell, so the containerized Postgres service has not been started yet.
- Real online migration validation with `uv run alembic upgrade head` is still pending until Docker is available.
- The backend framework is FastAPI.
- Dependency management is `uv`.
- Auth should be shaped around provider-neutral OIDC/JWT claims with a local/test bypass.
- Current local/test auth behavior:
  - `GET /me` returns a development coach when local auth is allowed.
  - development coach id: `Luis-dev-coach`
  - development coach email: `luisrivglez@gmail.com`
  - development coach display name: `Luis`
  - production mode or disabled local bypass returns `401 Unauthorized`.
- Config decisions:
  - environments are `development`, `test`, and `production`
  - `database_url` defaults to the local Docker Compose database `garmin_api_coach_dev`
  - `local_auth_bypass_enabled` controls the temporary local/test auth bypass
  - `is_local_auth_allowed()` prevents local bypass from working in production
- Clerk is the first auth provider to evaluate when real coach login and frontend work begin.
- Auth0 is the main fallback if API-first or enterprise auth needs become more important.
- Garmin account authorization must stay separate from platform coach login.
- The first development LLM provider is local Ollama with `phi4:14b-fp16`.
- The first production LLM provider is OpenAI.
- The current `Activities.csv` is preliminary and only supports monthly activity-count ingestion.
- The full Garmin export has arrived as a ZIP with structured JSON and nested FIT files.
- The first real importer should target `DI_CONNECT/DI-Connect-Fitness/*_summarizedActivities.json`.
- The export contains 3175 summarized activity records.
- The export contains 18597 uploaded FIT files inside nested ZIPs, but FIT parsing should come later.

Best next step:

After Docker is installed or available on PATH, start local Postgres and run the first migration. Then build the Garmin ZIP structure inspector.

Already created in the first build session:

1. `uv` Python project setup inside `Garmin App/`.
2. FastAPI app structure.
3. Health endpoint.
4. First health endpoint test.
5. Basic README.
6. `.gitignore`.
7. GitHub repository connection and initial push.

Already created in the second build session:

1. Config module.
2. Local/test auth dependency that injects a development coach.
3. Protected `GET /me` endpoint to prove the dependency works.
4. Tests for settings and local/test auth behavior.
5. Scope note explaining why email is currently a plain string and when to add email validation.

Already created in the third build session:

1. Docker Compose Postgres service.
2. SQLAlchemy and Alembic setup.
3. Initial database models:
   - coaches
   - clients
   - data_imports
   - raw_records
   - activity_type_mappings
   - activities
4. Local ignored raw-data folder:
   - `data/raw/`
5. Database setup tests.
6. Cleanup check found no stale files, duplicated modules, or unused project files worth removing.
7. Changes were committed and pushed to `origin/main`:
   - `fc35e0c Add auth and database foundation`

Next build session should create only after checkpoint approval:

1. Verify Docker is installed or available on PATH.
2. Run `docker compose up -d`.
3. Run `uv run alembic upgrade head`.
4. Build Garmin ZIP structure inspector.
5. Build Garmin summarized activities adapter.
6. Basic tests for parsing and import validation.

Reason:

This gives the project a deployable backend base, ownership model, data traceability, and a working ingestion path based on the actual Garmin export structure.

Do not start with:

- polished frontend
- client login
- Garmin OAuth
- OpenAI integration
- workout planning
- detailed running analytics
- detailed FIT parsing

Those depend on the backend foundation and the summarized JSON importer being stable first.
