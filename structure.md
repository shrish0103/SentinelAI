# SentinelAI File Map

## Root

- `readme.md` -> Project overview, feature summary, setup notes
- `SYSTEM_DESIGN.md` -> Architecture and system behavior reference
- `structure.md` -> Central map of file responsibilities
- `pyproject.toml` -> Project metadata and dependencies
- `requirements.txt` -> Simple pip install path for runtime dependencies
- `.env.example` -> Sample environment configuration without secrets
- `.gitignore` -> Local environment and generated file exclusions

## Application

- `app/main.py` -> FastAPI entrypoint and lifespan wiring

### API

- `app/api/router.py` -> Top-level API router
- `app/api/routes/alerts.py` -> `/alert` ingestion endpoint
- `app/api/routes/resume.py` -> `/resume/ask` portfolio assistant endpoint
- `app/api/routes/health.py` -> `/health/check` service health endpoint
- `app/api/routes/logs.py` -> `/logs` event query endpoint
- `app/api/routes/admin.py` -> `/admin/exec` admin command endpoint
- `app/api/routes/privacy.py` -> Public `/privacy-policy` page for Telegram BotFather

### Core

- `app/core/config.py` -> Environment-driven settings
- `app/core/dependencies.py` -> Shared dependency providers

### Schemas

- `app/schemas/alert.py` -> Alert payload and event response schemas
- `app/schemas/resume.py` -> Resume question and answer schemas
- `app/schemas/health.py` -> Health check response schemas
- `app/schemas/admin.py` -> Admin command request and response schemas
- `app/schemas/log.py` -> Log query response schemas

### Services

- `app/services/event_store.py` -> Async in-memory event persistence with structured internal failure events
- `app/services/notifier.py` -> Telegram notification delivery via aiogram with formatted alert messages
- `app/services/llm.py` -> Provider-agnostic LLM service with provider/model-aware exception details
- `app/services/health.py` -> Service registry and health probes
- `app/services/admin.py` -> Safe admin command execution

## Tests

- `tests/test_app.py` -> API smoke tests for the first bootstrap slice
