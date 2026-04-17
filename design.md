# 📐 SentinelAI — System Design

## 🧠 Overview

SentinelAI is a **personal control plane** that unifies:

* System monitoring
* Alerting infrastructure
* AI-powered portfolio interaction

It is designed with **production-grade backend principles**:

* stateless APIs
* async processing
* provider abstraction
* structured event ingestion

---

## 🏗️ High-Level Architecture

```
[ Services / Apps ]
        │
        ▼
   /alert endpoint
        │
        ▼
 ┌────────────────────┐
 │   FastAPI Core     │
 │────────────────────│
 │ Alert Processor    │
 │ AI Layer           │
 │ Health Engine      │
 │ Logging Layer      │
 └────────────────────┘
        │
        ├── Telegram Bot
        ├── LLM Provider (OpenRouter/OpenAI/Ollama)
        └── Storage (DB/File)
```

---

## ⚙️ Core Components

### 1. Alert Ingestion Layer

* Entry point: `/alert`
* Accepts structured events
* Validates and normalizes payload

### 2. Event Processing Layer

* Applies:

  * deduplication (future)
  * severity classification
* Triggers notifications

---

### 3. AI Layer (`/resume/ask`)

* Provider-agnostic LLM abstraction
* Injects structured context (resume, projects)
* Handles fallback if provider fails

---

### 4. Telegram Command Layer

#### Roles:

* **Owner**

  * full access
  * system control
* **Visitor**

  * AI-only interaction

---

### 5. Health Monitoring Engine

* Checks:

  * APIs
  * DBs
  * external services
* Can run:

  * on-demand
  * scheduled (future)

---

### 6. Logging System

Stores:

* alerts
* errors
* AI failures
* admin actions

---

## 🧱 Event Schema (Standardized)

All alerts must follow:

```json
{
  "app_name": "portfolio-api",
  "service": "payment-service",
  "level": "critical",
  "message": "Stripe timeout",
  "exception": {
    "type": "TimeoutError",
    "message": "Request timed out",
    "trace": "optional stack trace"
  },
  "timestamp": "ISO-8601"
}
```

### Why this matters:

* consistent debugging
* filtering & querying
* future analytics

---

## 🤖 LLM Provider Abstraction

```python
class LLMProvider:
    async def generate(self, prompt: str) -> str:
        pass
```

### Supported:

* OpenRouter
* OpenAI
* Ollama

---

## 🚨 Failure Handling (Critical Design)

### OpenRouter Failure Strategy

If:

* API error
* timeout
* rate limit

Then:

1. Log error
2. Trigger internal alert
3. Notify via Telegram

#### Example Alert:

```json
{
  "app_name": "sentinel-ai",
  "service": "llm-provider",
  "level": "critical",
  "message": "OpenRouter request failed",
  "exception": {
    "type": "ProviderError",
    "message": "429 rate limit"
  }
}
```

---

## 🔁 Future Enhancements

* Queue system (Redis / RabbitMQ)
* Vector search (RAG)
* Dashboard UI
* Alert deduplication
* Rate limiting
* Multi-user system

---

## 🧠 Design Philosophy

SentinelAI is built as:

> “A lightweight, extensible control plane for personal infrastructure”
