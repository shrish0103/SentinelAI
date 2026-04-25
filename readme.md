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

### Telegram Bot and Portfolio Commands

The Telegram bot (`aiogram`) is the primary interface for both the owner and guests. It now supports specialized portfolio commands:

- `/resume`: Returns Shrish's headline and automatically sends the latest `resume.pdf`.
- `/education`: Returns academic background (IMSEC Ghaziabad, etc.) with AI fallback if data is missing.
- `/projects`: Returns the top 3 key projects with AI fallback.
- `/certifications`: Returns professional certifications.
- `/logs [n]`: (Admin only) Retrieve the last `n` system logs (default 5).

### AI Reliability & Fallback

SentinelAI treats LLM uptime as a priority. If the primary provider (e.g., OpenRouter with GPT-OSS) fails due to a 503 or timeout, the system automatically:
1.  **Falls back** to a secondary reliable model (`google/gemini-2.0-flash-exp:free`).
2.  **Alerts the owner** via Telegram that a fallback was used.
3.  **Logs the actual model name** used for the response to ensure transparency.


### Health Monitoring

Poll `/health/check` to inspect the status of any registered service, including databases, external APIs, LLM providers, or your own microservices. Queryable per-service for granular diagnostics.

### Structured Logging & Performance

Every significant event is logged, including alerts, exceptions, AI failures, and admin actions. To maintain high performance:
- **Buffer Limit**: The in-memory event store keeps only the last **200 logs**, discarding older ones to prevent memory bloat.
- **Parametric Logs**: The `/logs` command supports custom limits (e.g., `/logs 20`) capped at 50 for readability.

---

## API & Command Reference

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/alert` | Ingest a structured alert event |
| `POST` | `/resume/ask` | Ask the AI portfolio assistant |
| `GET` | `/health/check` | Check service health with optional `?service=` |
| `GET` | `/logs` | Retrieve recent system logs |
| `POST` | `/admin/exec` | Execute owner-only admin commands |

### Bot Commands (Telegram)

| Command | Role | Description |
|---------|------|-------------|
| `/resume` | Guest/Admin | Text summary + Download `resume.pdf` |
| `/education` | Guest/Admin | Academic background |
| `/projects` | Guest/Admin | Key project portfolio |
| `/certifications`| Guest/Admin | Professional certs |
| `/logs [n]` | Admin | View last `n` system events |
| `/ping [target]` | Admin | Test network connectivity |
| `/ai` | Admin | Check current LLM provider health |

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

---

## 🚀 New in V2.0: Portfolio Control Plane

We have recently refactored the core to support high-end portfolio demonstrations and production-grade observability.

### 🎭 Advanced Identity Matrix
The bot now dynamically tracks user personas via a **Redis-backed session hash**:
- **👑 Admin Mode**: Full access to live telemetry and production logs (restricted to `OWNER_TELEGRAM_IDS`).
- **👤 Guest Mode**: AI-powered professional representative grounded in resume context.
- **🎭 Demo Mode**: A "DevOps Sandbox" for visitors to test diagnostics and alerts using **Mock Data** and a **Dummy Sandbox Group**.
- **🤖 AI Modifiers**: Real-time toggles between 'Resume-Grounded' and 'General Knowledge' LLM modes.

### 🏗️ Architectural Upgrades
- **Modular Command-Handler Pattern**: A decoupled **Router-Handler** architecture using self-registering units for zero-friction feature expansion.
- **Narrative Logging**: Every system event is captured with rich metadata (intent, persona, latency) for narrative, cross-service auditing.
- **Upstash Redis Session Layer**: High-performance, persistent state management for multi-account RBAC.

> Built with Antigravity for Shrish Gupta's Professional Architecture
