# SentinelAI — System Design

## Overview

SentinelAI is a personal control plane that unifies alert ingestion, AI-powered portfolio interaction, and service health monitoring into a single, self-hosted backend system.

It is built around four principles:

**Single-source alerting** — Every service pushes to one `/alert` endpoint instead of maintaining its own notification logic. This enforces a consistent schema and centralizes all observability in one place.

**Provider abstraction** — The LLM provider is a runtime configuration, not a code dependency. The rest of the system never references a concrete provider class.

**Observability of the observer** — SentinelAI monitors itself. LLM failures, health check errors, and bot failures all flow through the same alert pipeline as any other service event.

**Non-blocking I/O** — All outbound operations (Telegram notifications, LLM calls, health checks) are async. Alert ingestion returns immediately after validation; dispatch is decoupled from the request lifecycle.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   External Layer                        │
│    Services / Apps / Telegram Users / HTTP Clients      │
└────────────┬───────────────────────────┬────────────────┘
             │                           │
         REST API                  Telegram Bot
             │                           │
┌────────────▼───────────────────────────▼────────────────┐
│                    FastAPI Core                         │
│                                                         │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │
│   │   Alert     │   │   AI        │   │   Health    │  │
│   │  Processor  │   │   Layer     │   │   Engine    │  │
│   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘  │
│          │                 │                  │         │
│   ┌──────▼─────────────────▼──────────────────▼──────┐  │
│   │              Logging & Event Bus                  │  │
│   └──────────────────────┬───────────────────────────┘  │
└──────────────────────────┼──────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐   ┌──────▼──────┐  ┌─────▼──────┐
    │  Telegram │   │ LLM Provider│  │  Storage   │
    │    Bot    │   │(OpenRouter/ │  │(DB / File) │
    └───────────┘   │ OpenAI /    │  └────────────┘
                    │  Ollama)    │
                    └─────────────┘
```

---

## Request Flow Diagrams

### `POST /alert` — Alert Ingestion

```
Caller                  SentinelAI                    Outputs
──────                  ──────────                    ───────
POST /alert
  │
  ▼
Validate schema  ──── fail ──────────────────────►  400 Bad Request
  │
  ▼
Classify severity
(info / warning / critical)
  │
  ▼
Persist to log  ──────────────────────────────────►  Storage
  │
  ▼
Dispatch notification (async)  ───────────────────►  Telegram
  │
  ▼
Return 200 immediately
```

> Notification dispatch is fire-and-forget from the caller's perspective. The API returns 200 before Telegram confirms delivery.

---

### `POST /resume/ask` — AI Portfolio Assistant

```
Caller                  SentinelAI                    Outputs
──────                  ──────────                    ───────
POST /resume/ask
  │
  ▼
Validate question payload
  │
  ▼
Inject resume context into prompt
  │
  ▼
Call LLM Provider (async)
  │
  ├── success ─────────────────────────────────────►  Response to caller
  │
  └── failure
        │
        ▼
      Log provider error
        │
        ▼
      Trigger internal /alert
        │
        ▼
      Notify via Telegram  ─────────────────────────►  Owner notified
        │
        ▼
      Return graceful error to caller  ──────────────►  503 + retry hint
```

---

### `GET /health/check` — Service Health

```
Caller                  SentinelAI                    Outputs
──────                  ──────────                    ───────
GET /health/check?service=X
  │
  ▼
Resolve service target (URL / DB / provider)
  │
  ▼
Ping target (async, with timeout)
  │
  ├── healthy ─────────────────────────────────────►  { status: "ok" }
  │
  └── degraded / unreachable
        │
        ▼
      Classify as warning or critical
        │
        ▼
      Trigger internal /alert  ────────────────────►  Telegram notification
        │
        ▼
      Return { status: "degraded", detail: "..." }
```

---

## Component Design

### 1. Alert Ingestion Layer

**What it does:** Accepts structured events from any upstream service via a single `/alert` endpoint.

**Why it's designed this way:** A single shared endpoint means services don't own their own alerting logic. Any service that can make an HTTP POST can integrate instantly. Schema validation at ingestion ensures downstream components always receive clean, typed data.

**Responsibilities:**
- Parse and validate incoming payload against the event schema
- Normalize timestamps to ISO-8601
- Route to the Event Processing Layer

---

### 2. Event Processing Layer

**What it does:** Takes a validated event and decides what to do with it — persist it, classify it, and dispatch notifications.

**Why it's designed this way:** Processing is separated from ingestion so that the ingestion layer stays fast and stateless. Classification logic can evolve independently without touching the API layer.

**Responsibilities:**
- Apply severity classification (`info` → `warning` → `critical`)
- Persist to logging backend
- Trigger async notification dispatch
- Deduplication (planned — Redis-backed window comparison)

---

### 3. AI Layer

**What it does:** Handles natural language queries about Shrish's resume, skills, and projects via `/resume/ask`.

**Why it's designed this way:** The provider abstraction means the rest of the system never calls OpenRouter, OpenAI, or Ollama directly. Provider selection is config-driven. Swapping providers requires zero code changes.

**Responsibilities:**
- Inject structured resume context into every prompt
- Delegate generation to the configured provider
- **Autonomous Fallback**: Catch primary provider errors and immediately retry with a reliable fallback model (e.g., Gemini 2.0 Flash).
- **Transparency**: Track and log the `actual_model` name extracted from provider responses.
- Self-report failures and fallback events through the internal alert pipeline.


**Provider selection at runtime:**

```python
def get_provider(config: Config) -> LLMProvider:
    match config.MODEL_PROVIDER:
        case "openrouter": return OpenRouterProvider(config)
        case "openai":     return OpenAIProvider(config)
        case "ollama":     return OllamaProvider(config)
        case _:            raise ConfigError(f"Unknown provider: {config.MODEL_PROVIDER}")

class LLMProvider:
    async def generate(self, prompt: str) -> str:
        raise NotImplementedError
```

The `AI Layer` only ever holds a reference to `LLMProvider`. The concrete class is resolved once at startup and never referenced again.

---

### 4. Telegram Command Layer

**What it does:** Provides a real-time command interface over Telegram with role-based access control.

**Why it's designed this way:** Telegram handles authentication (user ID verification) and delivery reliability. This avoids building a custom dashboard for personal use.

**Role model:**

| Role | Access |
|------|--------|
| Owner (hardcoded Telegram ID) | Full system access — alerts, logs, admin commands, health status |
| Visitor (any other user) | AI assistant only — `/resume/ask` equivalent |

**No admin endpoint is publicly exposed.** All privileged operations go through the bot.

**Supported Command Paths:**
- **Portfolio (Public)**: `/resume` (PDF download), `/education`, `/projects`, `/certifications`.
- **Diagnostics (Admin)**: `/logs [n]`, `/ping <alias>`, `/ai`.


---

### 5. Health Monitoring Engine

**What it does:** Pings registered services and reports their status on demand.

**Why it's designed this way:** Health checks are pull-based (on-demand via API) in the current design, keeping the system simple. Push-based scheduled polling is on the roadmap but deliberately deferred until the alert pipeline is proven stable.

**Responsibilities:**
- Resolve service target from query param or config
- Async ping with configurable timeout
- Classify result and trigger alert if degraded
- Return structured status response

---

**Why it's designed this way:** All four event types (alerts, exceptions, AI failures, admin actions) share the same log schema. A single `/logs` endpoint surfaces everything. For stability, the system uses a **Circular Buffer** (in-memory) approach.

**Performance Constraints:**
- **Log Retention**: The `EventStore` limits logs to the last **200 entries**. Older events are evicted to prevent memory bloat.
- **Parametric Querying**: The `/logs` command supports a `limit` parameter to retrieve a specific window of history.


**Logged event types:**
- Inbound alerts from external services
- AI provider failures and fallback events
- Health check results (degraded/unreachable only)
- Admin commands executed via Telegram

---

## Event Schema

All system events — whether from external services or generated internally — follow one schema:

```json
{
  "app_name": "portfolio-api",
  "service": "payment-service",
  "level": "critical",
  "message": "Stripe timeout after 30s",
  "exception": {
    "type": "TimeoutError",
    "message": "Request timed out",
    "trace": "optional stack trace"
  },
  "timestamp": "2025-01-15T14:32:00Z"
}
```

**Why a shared schema matters:**
- Any component can emit an alert — including SentinelAI itself
- Filtering, querying, and future analytics work across all event sources
- Debugging is consistent regardless of which service originated the event

---

## LLM Failure Handling

Free-tier and third-party LLM providers are inherently unreliable — they can be rate-limited, deprecated, or go offline without warning. SentinelAI treats provider failures as first-class system events.

**Failure triggers:**
- HTTP 4xx / 5xx from provider API
- Request timeout exceeded
- Malformed or empty response

**Response sequence:**

```
1. Catch primary provider exception (503, Timeout, Network)
2. Log full error context (provider, model, error type, timestamp)
3. **Attempt Internal Fallback**: Instantiate secondary provider using `google/gemini-2.0-flash-exp:free`
4. If Fallback succeeds:
   - Emit `warning` alert via /alert ("Primary failed, using fallback")
   - Notify owner with the success details
   - Return fallback response to user
5. If Fallback fails or no fallback is possible:
   - Emit `critical` alert via /alert
   - Send critical notification to owner
   - Return 503 to caller with a retry suggestion
```


**Example self-generated alert:**

```json
{
  "app_name": "sentinel-ai",
  "service": "llm-provider",
  "level": "critical",
  "message": "OpenRouter request failed — 429 rate limit exceeded",
  "exception": {
    "type": "ProviderError",
    "message": "429 Too Many Requests"
  },
  "timestamp": "2025-01-15T14:33:01Z"
}
```

The system monitoring itself through its own alert pipeline is intentional — it means LLM reliability is observable with zero additional tooling.

---

## Async Model

All I/O-bound operations are async:

| Operation | Handling |
|-----------|----------|
| Telegram notification dispatch | Fire-and-forget after alert is persisted |
| LLM API call | Awaited with timeout; failure triggers alert |
| Health check ping | Awaited with configurable timeout per service |
| Log persistence | Awaited before 200 is returned |

Alert ingestion returns to the caller immediately after validation and persistence. Notification delivery is non-blocking — a slow Telegram API or LLM provider never adds latency to the `/alert` response.

---

## Security Model

| Concern | Approach |
|---------|----------|
| Admin access | Telegram user ID allowlist — no public admin endpoints |
| API secrets | Environment variables only — never in code or logs |
| Input validation | Schema validation on all inbound payloads |
| Visitor isolation | Bot role check on every command before execution |

---

## Roadmap

| Feature | Purpose |
|---------|---------|
| Redis-backed alert queue | Decouple ingestion from dispatch; enable retries |
| Alert deduplication | Suppress repeated identical events within a time window |
| Vector search (RAG) | Ground AI responses in richer, searchable resume data |
| Scheduled health polling | Proactive monitogit checkout -b feature/project-bootstrap
ring without manual checks |
| Rate limiting | Protect `/alert` and `/resume/ask` from abuse |
| Dashboard UI | Visual log explorer and alert timeline |
| Multi-user system | Extend role model beyond owner/visitor |

---

## V2.0 Modular Architecture Update

### 🧩 1. Modular Router-Handler Pattern
As the system grew, we transitioned from a monolithic `AdminService` to a highly decoupled **Router-Handler** pattern.
- **Dynamic Handler Discovery**: Using a singleton `ActionRegistry`, handlers now self-register on startup.
- **Dependency Injection**: The `AdminRouter` performs automated constructor injection, providing services like `HealthService` and `EventStore` to handlers only when needed.
- **Separation of Concerns**: Each command unit (e.g., `DiagnosticsHandler`, `SystemHandler`) is isolated, ensuring that a failure in one command does not affect the core bot logic.

### 👥 2. Redis-Backed Identity Switching (RBAC)
We replaced transient in-memory flags with a persistent, distributed session model using **Upstash Redis Hashes**.
- **Unified State**: The key `user_session:{user_id}` serves as the single source of truth for a user's `role` (Admin, Guest, Demo) and `ai_mode`.
- **Identity Sandbox**: Demo mode is now fully isolated. When active, diagnostic handlers switch from production APIs to mock data providers, ensuring zero production data leakage during showcases.
- **Security Gating**: A strict authorization layer in the **Admin Router** verifies every intent against the session role, preventing unauthorized access to restricted features.

### 📡 3. Observable Narrative Logging (V2)
Logging has been upgraded to support **Diagnostic Contexts**.
- Every command execution is wrapped in a metadata-rich context, including the user's role and the AI's grounding state.
- Narrative logs now allow for seamless debugging of "Persona Switching" and "AI Grounding" logic in a production environment.

---
*V2.0 Documentation Update — Refactored for Multi-Account Scalability*
