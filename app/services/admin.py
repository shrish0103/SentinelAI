from schemas.admin import AdminCommandResponse
from services.event_store import EventStore
from services.health import HealthService
from services.llm import LLMService, LLMServiceError
from core.prompts import get_admin_help_text


class AdminService:
    def __init__(
        self,
        event_store: EventStore,
        health_service: HealthService,
        llm_service: LLMService,
    ) -> None:
        self._event_store = event_store
        self._health_service = health_service
        self._llm_service = llm_service

    async def execute(self, command: str, is_admin: bool = False) -> AdminCommandResponse:
        normalized = command.strip().lower()
        output = ""

        # Admin-only commands
        if is_admin:
            if normalized == "ping":
                output = "pong"
            elif normalized.startswith("check "):
                tokens = normalized.split(" ", 1)
                service_name = tokens[1] if len(tokens) > 1 else "api"
                health = await self._health_service.check(service_name)
                output = health.model_dump_json(indent=2)
            elif normalized == "logs":
                events = await self._event_store.list_events(limit=5)
                output = f"Recent events: {len(events)}"
            elif normalized in ("/admin", "help", "/start"):
                output = get_admin_help_text(is_admin=True)

        # Fallback for non-admins or unknown admin commands (route to LLM)
        if not output:
            if normalized in ("/admin", "help", "/start"):
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
