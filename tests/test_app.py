from httpx import ASGITransport, AsyncClient
import pytest

from core.dependencies import get_llm_service, get_notifier
from main import app
from schemas.alert import EventRecord
from services.llm import LLMServiceError
from services.notifier import TelegramNotifier


class StubLLMService:
    provider_name = "stub"
    using_fallback = False

    async def answer_question(self, question: str) -> str:
        return f"stubbed answer for: {question}"


class StubNotifier:
    async def notify_alert(self, event) -> bool:
        return False


class FailingLLMService:
    provider_name = "openrouter"
    using_fallback = False

    async def answer_question(self, question: str) -> str:
        raise LLMServiceError(
            provider="openrouter",
            model="qwen/qwen-2.5-7b-instruct",
            category="network-connectivity",
            detail="Connection to https://openrouter.ai/api/v1 could not be established",
            hint="Check provider reachability or retry shortly.",
        )


@pytest.mark.asyncio
async def test_alert_ingestion() -> None:
    app.dependency_overrides[get_notifier] = lambda: StubNotifier()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/alert",
            json={
                "app_name": "portfolio-api",
                "service": "auth-service",
                "level": "critical",
                "message": "JWT validation failed",
            },
        )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_resume_endpoint_returns_answer() -> None:
    app.dependency_overrides[get_llm_service] = lambda: StubLLMService()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/resume/ask",
            json={"question": "What does Shrish specialize in?"},
        )

    assert response.status_code == 200
    assert "stubbed answer" in response.json()["answer"].lower()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_privacy_policy_endpoint_returns_html() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/privacy-policy")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SentinelAI Privacy Policy" in response.text


@pytest.mark.asyncio
async def test_cors_allows_configured_frontend_origin() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/resume/ask",
            headers={
                "Origin": "https://shrish0.github.io",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://shrish0.github.io"


@pytest.mark.asyncio
async def test_resume_failure_keeps_specific_provider_context() -> None:
    app.dependency_overrides[get_llm_service] = lambda: FailingLLMService()
    app.dependency_overrides[get_notifier] = lambda: StubNotifier()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/resume/ask",
            json={"question": "What does Shrish specialize in?"},
        )

    assert response.status_code == 503
    app.dependency_overrides.clear()


def test_notifier_formats_rich_alert_message() -> None:
    notifier = TelegramNotifier.__new__(TelegramNotifier)
    event = EventRecord(
        id="evt-1",
        app_name="sentinel-ai",
        service="llm-provider",
        level="critical",
        message="Resume assistant request failed via openrouter:qwen/qwen-2.5-7b-instruct -> network-connectivity.",
        exception={
            "type": "LLMServiceError",
            "message": (
                "Provider 'openrouter' failed for model 'qwen/qwen-2.5-7b-instruct'. "
                "Category: network-connectivity. "
                "Detail: Connection to https://openrouter.ai/api/v1 could not be established. "
                "Hint: Check internet connectivity, DNS, firewall rules, or provider reachability.."
            ),
        },
        timestamp="2026-04-17T09:26:40.430875+00:00",
        source="internal",
    )

    message = notifier._format_message(event)
    assert "<b>ALERT</b>: <b>CRITICAL</b>" in message
    assert "<b>Exception Type</b>: <code>LLMServiceError</code>" in message
    assert "qwen/qwen-2.5-7b-instruct" in message
