# SentinelAI

> **Personal Control Plane for Backend Systems and AI Portfolio**

SentinelAI is a self-hosted intelligence layer that sits over your backend infrastructure, routing alerts, answering portfolio questions with AI, monitoring service health, and giving you Telegram-based command access from anywhere.

---

## Why SentinelAI?

Most personal backend projects are either observable or interactive, rarely both. SentinelAI unifies:

- A structured alerting pipeline that ingests events from any service
- An AI assistant trained on your resume and portfolio
- A health monitoring layer across APIs, databases, and providers
- A Telegram bot with role-based access control

One system. Full visibility. Yours to own.

---

## Core Features

### Alert Pipeline

Expose a single `/alert` endpoint across all your services. Events are ingested, classified by severity, stored, and optionally routed to Telegram.

| Severity | Use Case |
|----------|----------|
| `info` | Routine events, deploys, state changes |
| `warning` | Degraded performance, retries, soft failures |
| `critical` | Auth failures, crashes, payment errors |

### AI Portfolio Assistant

Ask natural language questions about Shrish's skills, projects, and experience via `/resume/ask`. The LLM layer is provider-agnostic and can call OpenRouter, OpenAI, Ollama, or a local fallback provider depending on environment configuration.

### LLM Failure Observability

When an AI provider fails, SentinelAI logs the failure, emits an internal alert, and can notify the owner through Telegram. AI reliability is treated as a first-class system concern.

### Telegram Bot and Notifications

The current bootstrap is wired for `aiogram`. Telegram is used for notification delivery and is the intended path for owner-only command access as the bot layer expands.

### Health Monitoring

Poll `/health/check` to inspect the status of any registered service, including databases, external APIs, LLM providers, or your own microservices. Queryable per-service for granular diagnostics.

### Structured Logging

Every significant event is logged, including alerts, exceptions, AI failures, and admin actions, giving you a complete audit trail without external tooling.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/alert` | Ingest a structured alert event |
| `POST` | `/resume/ask` | Ask the AI portfolio assistant |
| `GET` | `/health/check` | Check service health with optional `?service=` |
| `GET` | `/logs` | Retrieve recent system logs |
| `POST` | `/admin/exec` | Execute owner-only admin commands |

### Example `POST /alert`

```json
{
  "app_name": "payment-system",
  "service": "stripe-handler",
  "level": "critical",
  "message": "Payment failed"
}
```

### Example `POST /resume/ask`

```json
{
  "question": "What does Shrish specialize in?"
}
```

### Example `POST /admin/exec`

```json
{
  "command": "check api"
}
```

---

## Model Configuration

SentinelAI is not tied to one provider. Swap models through environment variables.

```env
MODEL_PROVIDER=openrouter
MODEL_NAME=openai/gpt-4o-mini
API_KEY=your_openrouter_key
```

Supported providers:

- `openrouter`
- `openai`
- `ollama`
- `local`

If `MODEL_PROVIDER=openrouter`, `/resume/ask` uses the OpenRouter chat completions API with the configured key from `.env`.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI |
| Bot | aiogram |
| AI | OpenRouter / OpenAI / Ollama / local fallback |
| HTTP Client | httpx |
| Config | pydantic-settings |

---

## Running Locally

```bash
git clone <repo>
cd SentinelAI
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov
uvicorn app.main:app --reload
```

Create a `.env` file from `.env.example`.

Minimal OpenRouter setup:

```env
MODEL_PROVIDER=openrouter
MODEL_NAME=openai/gpt-4o-mini
API_KEY=your_openrouter_key
```

Optional Telegram setup:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
OWNER_TELEGRAM_IDS=your_numeric_telegram_user_id,another_owner_id
```

The current bootstrap already includes:

- An in-memory event store for alerts and logs
- A real HTTP-backed provider layer for OpenRouter, OpenAI, and Ollama
- A local fallback provider for offline development
- Telegram notification delivery through `aiogram`

Project structure is tracked in `structure.md` to keep file ownership clear as the system grows.

### Quick API Smoke Test

Once the server is running:

```bash
curl -X POST http://127.0.0.1:8000/resume/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"What does Shrish specialize in?\"}"
```

---

## Security

- Auth is intended to be enforced through Telegram user ID verification
- Secrets live in environment variables, not in source control
- Input validation is handled through typed request schemas

---

## Roadmap

- [ ] Redis-backed queue system
- [ ] Vector search over resume and portfolio context
- [ ] Full Telegram command router
- [ ] Alert deduplication
- [ ] Scheduled health polling
- [ ] Dashboard UI

---

## Author

**Shrish Gupta**  
Backend Engineer focused on FastAPI, microservices, distributed systems, observability, and applied AI
