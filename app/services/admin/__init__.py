import logging
from typing import Any
from core.config import Settings
from services.health import HealthService
from services.event_store import EventStore
from services.notifier import TelegramNotifier
from services.demo import DemoService
from services.admin.interfaces import LLMServiceProtocol
from services.admin.router import AdminRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AdminCommandResponse(BaseModel):
    status: str
    output: str
    document_path: str | None = None

class AdminService:
    """
    A thin facade over the AdminRouter.
    Maintains the existing class interface to prevent breaking changes in the rest of the app,
    but delegates all logic to the new Command-Handler architecture.
    """
    def __init__(
        self,
        settings: Settings,
        health_service: HealthService,
        event_store: EventStore,
        notifier: TelegramNotifier,
        demo_service: DemoService,
        llm_service: LLMServiceProtocol
    ) -> None:
        self._router = AdminRouter(
            settings=settings,
            health_service=health_service,
            event_store=event_store,
            notifier=notifier,
            demo_service=demo_service,
            llm_service=llm_service
        )

    async def execute(self, command: str, is_admin: bool = False, user_id: int = 0) -> AdminCommandResponse:
        """Entry point that delegates to the specialized AdminRouter."""
        result = await self._router.dispatch(
            raw_command=command,
            is_admin_context=is_admin,
            user_id=user_id
        )
        
        return AdminCommandResponse(
            status=result["status"],
            output=result["output"],
            document_path=result.get("document_path")
        )
