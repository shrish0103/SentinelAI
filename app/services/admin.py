from schemas.admin import AdminCommandResponse
from services.event_store import EventStore
from services.health import HealthService
from services.llm import LLMService, LLMServiceError
from services.notifier import TelegramNotifier
from core.config import Settings
from core.prompts import get_admin_help_text


class AdminService:
    def __init__(
        self,
        event_store: EventStore,
        health_service: HealthService,
        llm_service: LLMService,
        notifier: TelegramNotifier,
        settings: Settings,
    ) -> None:
        self._event_store = event_store
        self._health_service = health_service
        self._llm_service = llm_service
        self._notifier = notifier
        self._settings = settings

    async def execute(self, command: str, is_admin: bool = False) -> AdminCommandResponse:
        normalized = command.strip().lower()
        output = ""

        # Admin-only commands
        if is_admin:
            if normalized == "ping" or normalized == "/ping":
                targets = self._settings.service_targets
                output = "🚀 *Service Registry*\n\n"
                for alias, url in targets.items():
                    output += f"• `{alias}`: {url}\n"
                output += "\n💡 _Use `/ping <alias>` to test a specific endpoint._"
            elif normalized.startswith("ping ") or normalized.startswith("/ping "):
                tokens = normalized.split(" ")
                alias = tokens[1]
                health = await self._health_service.check(alias)
                output = f"📡 *Ping Result for {alias}:*\n\n"
                if health.checks:
                    check = health.checks[0]
                    output += f"Status: {check.status.upper()}\nDetail: {check.detail}"
                else:
                    output += "❌ Alias not found in registry."
            elif normalized == "test" or normalized == "/test":
                output = (
                    "🧪 *SentinelAI Test Suite*\n\n"
                    "• `/test telegram` - Send a test alert to verify the notification pipeline.\n"
                    "• `/test llm` - Verify AI provider connectivity and persona consistency."
                )
            elif normalized == "/test telegram":
                from services.event_store import InternalEvent
                test_event = InternalEvent(
                    id="test-id",
                    timestamp="now",
                    service="admin-test",
                    message="✅ Manual notification test successful.",
                    level="info"
                )
                await self._notifier.notify_alert(test_event)
                output = "✅ Test alert dispatched to Telegram."
            elif normalized.startswith("check ") or normalized.startswith("/check "):
                tokens = normalized.split(" ", 1)
                service_name = tokens[1] if len(tokens) > 1 else "api"
                health = await self._health_service.check(service_name)
                output = f"🔍 *Health Report: {service_name}*\n```json\n" + health.model_dump_json(indent=2) + "\n```"
            elif normalized == "logs" or normalized == "/logs":
                events = await self._event_store.list_events(limit=5)
                output = "📋 *System Logs (Last 5)*\n\n"
                for e in events:
                    output += f"• `[{e.level.upper()}]` {e.service}: {e.message}\n"
            elif normalized == "ai status" or normalized == "/ai":
                health = await self._health_service.check("llm")
                output = f"🤖 *AI Provider Status ({self._settings.model_provider})*\n\n"
                if health.checks:
                    output += f"Status: {health.checks[0].status.upper()}\nDetail: {health.checks[0].detail}"
            elif normalized == "/help_guest":
                output = get_admin_help_text(is_admin=False)
            elif normalized in ("/admin", "help", "/start", "/help"):
                output = get_admin_help_text(is_admin=True)

        # Fallback for non-admins or unknown commands
        if not output:
            if normalized in ("/help", "/start", "help"):
                output = get_admin_help_text(is_admin=False)
            else:
                try:
                    output = await self._llm_service.answer_question(command)
                except LLMServiceError as exc:
                    output = f"Sorry, I encountered an error: {exc.user_message}"

        await self._event_store.record_internal_event(
            service="admin-command",
            message=f"Admin command executed (is_admin={is_admin}): {command}",
            level="info",
        )
        return AdminCommandResponse(status="ok", output=output)
