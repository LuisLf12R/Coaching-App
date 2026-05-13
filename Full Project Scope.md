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

Observed UDS aggregator shape:

- 19 UDS files
- 1732 daily records seen
- 984 daily records with useful wellness signals
- daily Body Battery stats
- all-day stress aggregates
- resting heart rate, steps, intensity minutes, respiration, and Pulse Ox values

UDS records before wearable wellness data can be calorie-only. The normalized UDS importer should keep the source traceable but only create daily wellness metrics when observed readiness-relevant signals are present.

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

Initial implementation status:

- deterministic activity overview service created
- coach-scoped `/analytics/activity-overview` endpoint created
- activity count, active days, active weeks, sport mix, weekly/monthly activity buckets, running summary, strength summary, and missing-data warnings implemented
- API response tests added against known activity records
- completed as the first Phase 4 slice on 2026-05-13

### Phase 5: Readiness Foundation

Goal: create the readiness engine structure without pretending recovery data exists before those Garmin JSON sources are imported.

Build:

- readiness factor model
- readiness status output
- missing recovery-data warnings
- placeholder-free scoring, no fake health inference
- source attribution for contributing activity records
- Garmin readiness and sleep source mapping
- Garmin health, wellness, and load source mapping

Validation:

- readiness output identifies which source files contributed each available activity and recovery factor
- missing HRV/stress/load/health-status data is explicit when unavailable
- no false precision

Initial implementation status:

- activity-only readiness service created
- coach-scoped `GET /readiness/summary` endpoint created
- status output limited to `green`, `yellow`, or `red`
- factors report source files and missing inputs
- Garmin `TrainingReadinessDTO` parser and database import service created
- `training_readiness_metrics` table created for daily Garmin readiness values
- readiness now uses the latest imported Garmin readiness score and level when available
- Garmin sleep data parser and database import service created
- `sleep_metrics` table created for daily Garmin sleep values
- readiness now uses the latest imported Garmin sleep score when available
- Garmin health-status data parser and database import service created
- `health_status_metrics` table created for daily Garmin health-status values
- readiness now uses the latest imported Garmin health-status metrics when available
- Garmin acute training load parser and database import service created
- `acute_training_load_metrics` table created for daily Garmin acute load values
- readiness now uses the latest imported Garmin acute load values and ACWR status when available
- Garmin UDS daily wellness parser and database import service created
- `daily_wellness_metrics` table created for daily Garmin Body Battery, stress, resting heart rate, steps, respiration, intensity minutes, and Pulse Ox values
- readiness now uses the latest imported Garmin daily wellness Body Battery and stress values when available
- completed as Phase 5 slices on 2026-05-13

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

1. Initial FastAPI/`uv` scaffold accepted as the first checkpoint. Completed.
2. Config module and local/test auth dependency created after Luis approved the shape. Completed.
3. Configure Postgres through Docker Compose after confirming Docker availability. Completed.
4. Create SQLAlchemy and Alembic setup. Completed.
5. Define initial models for coaches, clients, data imports, raw records, activity type mappings, and normalized activities. Completed.
6. Add project raw-data guidance for storing the Garmin export ZIP without committing sensitive source data. Completed.
7. Build Garmin export ZIP inspector. Completed.
8. Build Garmin summarized activities JSON adapter. Completed.
9. Import the 3175 summarized activity records for one initial client. Completed.
10. Expose API endpoints to query normalized activities and activity summaries. Completed.
11. Add tests for database import, API responses, and activity summary responses. Completed.
12. Add first deterministic activity analytics overview endpoint. Completed.
13. Add first readiness foundation endpoint with explicit missing recovery-data warnings. Completed.
14. Import Garmin `TrainingReadinessDTO` records and use the latest imported value in readiness. Completed.
15. Import Garmin sleep records and use the latest imported sleep score in readiness. Completed.
16. Import Garmin health-status records and use the latest imported health-status values in readiness. Completed.
17. Import Garmin acute training load records and use the latest imported load values in readiness. Completed.
18. Inspect Garmin UDS aggregator files and import daily wellness Body Battery and stress values into readiness. Completed.

This milestone proves the backend architecture, modular ingestion path, imported activity API, first deterministic analytics layer, and first source-attributed readiness API before parsing FIT files, importing broader health metrics, adding LLM analysis, or building UI.

## Open Questions

1. Should OpenAI be configured globally for the platform first, or should the schema support per-coach LLM provider settings from the beginning?
2. Should readiness summaries be persisted in `readiness_scores`, or should they stay computed on demand until LLM analysis needs stored snapshots?

## Handoff

Current implementation handoff is tracked in `PROJECT_STATUS.md`.

Keep this scope file focused on product direction, architecture, phase decisions, and open questions. Use `PROJECT_STATUS.md` for current code status, validation results, and next-step handoff notes.
