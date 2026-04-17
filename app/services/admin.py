from app.schemas.admin import AdminCommandResponse
from app.services.event_store import EventStore
from app.services.health import HealthService


class AdminService:
    def __init__(self, event_store: EventStore, health_service: HealthService) -> None:
        self._event_store = event_store
        self._health_service = health_service

    async def execute(self, command: str) -> AdminCommandResponse:
        normalized = command.strip().lower()
        if normalized == "ping":
            output = "pong"
        elif normalized.startswith("check "):
            service_name = normalized.split(" ", 1)[1]
            health = await self._health_service.check(service_name)
            output = health.model_dump_json(indent=2)
        elif normalized == "logs":
            events = await self._event_store.list_events(limit=5)
            output = f"Recent events: {len(events)}"
        else:
            output = "Unsupported command. Try 'ping', 'check <service>', or 'logs'."

        await self._event_store.record_internal_event(
            service="admin-command",
            message=f"Admin command executed: {command}",
            level="info",
        )
        return AdminCommandResponse(status="ok", output=output)
