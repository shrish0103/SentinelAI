from services.admin.interfaces import CommandHandler, CommandContext, CommandResult
from services.admin.formatter import AdminFormatter
from services.event_store import EventStore
from services.notifier import TelegramNotifier
from core.config import Settings
from schemas.alert import EventRecord
from datetime import datetime, timezone
from services.admin.registry import action_registry
from schemas.user import UserRole
from services.demo import DemoService

@action_registry.register("logs", "test")
class SystemHandler(CommandHandler):
    def __init__(self, settings: Settings, event_store: EventStore, notifier: TelegramNotifier, demo_service: DemoService) -> None:
        self._settings = settings
        self._event_store = event_store
        self._notifier = notifier
        self._demo_service = demo_service

    async def handle(self, ctx: CommandContext) -> CommandResult:
        formatter = AdminFormatter()
        
        # Branch 1: Logs (Mock if Demo)
        if ctx.intent in ("logs", "/logs"):
            if ctx.role == UserRole.DEMO:
                return CommandResult(success=True, data=None, message=self._demo_service.get_mock_logs())
            
            limit = 5
            if ctx.cmd_args and ctx.cmd_args[0].isdigit():
                limit = min(int(ctx.cmd_args[0]), 50)
            
            events = await self._event_store.list_events(limit=limit)
            return CommandResult(
                success=True,
                data=events,
                message=formatter.format_logs(events, limit)
            )
            
        # Branch 2: Test Telegram (Safe Sandbox)
        if ctx.intent == "test" and ctx.cmd_args and ctx.cmd_args[0] == "telegram":
            # Determine target chat and sandbox link
            target_chat = self._settings.telegram_chat_id
            sandbox_link = self._settings.dummy_alert_group_link or "https://t.me/your_dummy_group"
            
            if ctx.role == UserRole.DEMO:
                target_chat = self._settings.dummy_alert_group_id
            
            # Prepare test event
            test_event = EventRecord(
                id="test", 
                timestamp=datetime.now(timezone.utc), 
                service="demo-sandbox" if ctx.role == UserRole.DEMO else "admin-test", 
                app_name="sentinel-ai", 
                message=f"✅ Manual {'Demo' if ctx.role == UserRole.DEMO else 'Admin'} test successful.", 
                level="info", 
                source="internal"
            )
            
            # Dispatch
            success = await self._notifier.notify_alert(test_event, chat_id=target_chat)
            
            if ctx.role == UserRole.DEMO:
                return CommandResult(
                    success=success, 
                    message=f"✅ *Mock Alert Dispatched*\n\nI've sent a live telemetry event to the **SentinelAI Sandbox**.\n\n🔗 [Join Sandbox to view alerts]({sandbox_link})"
                )
            
            return CommandResult(success=success, message=f"✅ Test alert dispatched to {'Admin Group' if success else 'failed'}.")
            
        return CommandResult(success=False, data=None, message="❌ Unknown system command.")
