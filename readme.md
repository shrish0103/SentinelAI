# 🚀 SentinelAI

**Personal Control Plane for Backend Systems + AI Portfolio**

---

## 🧠 What is SentinelAI?

SentinelAI is a unified backend system that combines:

* 📡 Real-time alerting
* 🤖 AI-powered portfolio assistant
* 🧪 Service health monitoring
* 🔐 Role-based Telegram control

It acts as a **central intelligence layer** over your systems.

---

## ⚡ Key Capabilities

### 📡 Alert System

* Central `/alert` endpoint
* Structured event ingestion
* Telegram notifications
* Severity levels:

  * info
  * warning
  * critical

---

### 🤖 AI Portfolio (`/resume/ask`)

* Answers questions about:

  * skills
  * projects
  * experience
* Provider-agnostic LLM system
* Supports fallback strategy

---

### 🚨 LLM Failure Alerts (NEW)

If AI provider fails (e.g. OpenRouter):

* system logs error
* triggers internal alert
* sends Telegram notification

👉 Ensures **AI reliability is observable**

---

### 🔐 Telegram Bot

#### 👑 Owner

* full access
* system commands
* logs & alerts

#### 👤 Visitors

* AI-only interaction

---

### 🧪 Health Monitoring

* `/health/check`
* monitors services like:

  * APIs
  * DB
  * external providers

---

### 📜 Logging

* Alerts
* Exceptions
* AI failures
* Admin actions

---

## 🧱 Event Structure

All alerts follow a standard schema:

```json
{
  "app_name": "portfolio-api",
  "service": "auth-service",
  "level": "critical",
  "message": "JWT validation failed",
  "exception": {
    "type": "AuthError",
    "message": "Invalid token"
  }
}
```

---

## 🔌 API Endpoints

### POST `/alert`

```json
{
  "app_name": "payment-system",
  "service": "stripe-handler",
  "level": "critical",
  "message": "Payment failed"
}
```

---

### POST `/resume/ask`

```json
{
  "question": "What does Shrish specialize in?"
}
```

---

### GET `/health/check`

```
/health/check?service=supabase
```

---

### GET `/logs`

Retrieve system logs

---

### POST `/admin/exec`

```json
{
  "command": "check supabase"
}
```

---

## 🤖 Model Strategy

Provider-agnostic:

* OpenRouter
* OpenAI
* Ollama

---

### Config

```
MODEL_PROVIDER=openrouter
MODEL_NAME=qwen/qwen-2.5-7b-instruct
API_KEY=your_key
```

---

## ⚠️ Handling Model Instability

Free models may:

* become paid
* be rate-limited
* fail unexpectedly

SentinelAI handles this via:

* failure detection
* alerting
* fallback-ready design

---

## 🧱 Tech Stack

* FastAPI
* Telegram Bot (aiogram)
* LLM APIs
* Supabase (optional)
* Docker

---

## 🚀 Run Locally

```bash
git clone <repo>
cd sentinel-ai

pip install -r requirements.txt
uvicorn main:app --reload
```

---

## 🔐 Security

* Telegram ID-based auth
* No public admin endpoints
* Env-based secrets

---

## 💡 Roadmap

* [ ] Queue system (Redis)
* [ ] Vector search (RAG)
* [ ] Dashboard UI
* [ ] Alert deduplication
* [ ] Rate limiting

---

## 🧑‍💻 Author

Shrish Gupta
Backend Engineer — FastAPI, Microservices, Distributed Systems
