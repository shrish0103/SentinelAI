from schemas.admin import AdminCommandResponse
from services.event_store import EventStore
from services.health import HealthService
from services.llm import LLMService, LLMServiceError
from services.notifier import TelegramNotifier
import logging
from core.config import Settings
from core.prompts import get_admin_help_text

logger = logging.getLogger(__name__)


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
        logger.info(f"AdminService.execute called with command='{command}', is_admin={is_admin}")
        normalized = command.strip().lower()
        output = ""
        doc_path = None

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
                from datetime import datetime, timezone
                from schemas.alert import EventRecord
                test_event = EventRecord(
                    id="test-id",
                    timestamp=datetime.now(timezone.utc),
                    service="admin-test",
                    app_name="sentinel-ai",
                    message="✅ Manual notification test successful.",
                    level="info",
                    source="internal"
                )
                await self._notifier.notify_alert(test_event)
                output = "✅ Test alert dispatched to Telegram."
            elif normalized.startswith("check ") or normalized.startswith("/check "):
                tokens = normalized.split(" ", 1)
                service_name = tokens[1] if len(tokens) > 1 else "api"
                health = await self._health_service.check(service_name)
                output = f"🔍 *Health Report: {service_name}*\n```json\n" + health.model_dump_json(indent=2) + "\n```"
            elif normalized == "logs" or normalized == "/logs" or normalized.startswith("logs ") or normalized.startswith("/logs "):
                limit = 5
                tokens = normalized.split()
                if len(tokens) > 1 and tokens[1].isdigit():
                    limit = min(int(tokens[1]), 50) # Cap at 50 for message size limits
                
                events = await self._event_store.list_events(limit=limit)
                output = f"📋 *System Logs (Last {len(events)})*\n\n"
                for e in events:
                    # Escape special characters to avoid Markdown parsing errors
                    safe_msg = e.message.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")
                    output += f"• `[{e.level.upper()}]` {e.service}: {safe_msg}\n"

            elif normalized == "ai status" or normalized == "/ai":
                health = await self._health_service.check("llm")
                output = f"🤖 *AI Provider Status ({self._settings.model_provider})*\n\n"
                if health.checks:
                    output += f"Status: {health.checks[0].status.upper()}\nDetail: {health.checks[0].detail}"
            elif normalized == "/help_guest":
                output = get_admin_help_text(is_admin=False)
            elif normalized in ("/admin", "help", "/start", "/help"):
                output = get_admin_help_text(is_admin=True)

        # Fallback for non-admins or specific guest commands
        if not output:
            from resume import RESUME_DATA
            ai_invitation = "\n\n💡 _If you want to ask a question through AI, just type the question below!_"
            
            if normalized == "/resume":

                name = RESUME_DATA["basics"]["name"]
                headline = RESUME_DATA["basics"]["headline"]
                output = f"📄 *{name}'s Resume*\n\n"
                output += f"🚀 *Headline*: {headline}\n"
                output += ai_invitation
                doc_path = "app/resume.pdf"
            elif normalized in ("/education", "/academic"):
                edu = RESUME_DATA.get("sections", {}).get("education", {}).get("items", [])
                if edu:
                    output = "🎓 *Academic Background*\n\n"
                    for e in edu:
                        school = e["school"]
                        period = e.get("period", "")
                        desc = e.get("description", "").replace("<p>", "").replace("</p>", "").replace("<strong>", "*").replace("</strong>", "*")
                        output += f"• *{school}* ({period})\n{desc}\n\n"
                    output += ai_invitation
            elif normalized == "/projects":
                projects = RESUME_DATA.get("sections", {}).get("projects", {}).get("items", [])
                if projects:
                    output = "🚀 *Key Projects*\n\n"
                    for p in projects[:3]: # Limit to top 3 for brevity
                        name = p["name"]
                        desc = p.get("description", "").replace("<ul>", "").replace("</ul>", "").replace("<li>", "• ").replace("</li>", "\n").replace("<p>", "").replace("</p>", "").replace("<strong>", "*").replace("</strong>", "*")
                        output += f"* {name}\n{desc.strip()}\n\n"
                    output += ai_invitation
            elif normalized == "/certifications":
                certs = RESUME_DATA.get("sections", {}).get("certifications", {}).get("items", [])
                if certs:
                    output = "📜 *Professional Certifications*\n\n"
                    for c in certs:
                        issuer = f" ({c['issuer']})" if c['issuer'] else ""
                        output += f"• *{c['title']}*{issuer}\n"
                    output += ai_invitation
            elif normalized in ("/help", "/start", "help"):
                output = get_admin_help_text(is_admin=False)

            else:
                try:
                    output, actual_model, used_fallback = await self._llm_service.answer_question(command)
                    
                    if used_fallback:
                        # Inform admin about fallback success
                        event = await self._event_store.record_internal_event(
                            service="llm",
                            message=f"⚠️ Primary LLM failed. Fallback successful using: {actual_model}",
                            level="warning"
                        )
                        await self._notifier.notify_alert(event)
                except LLMServiceError as exc:
                    # Record the permanent failure in the event store
                    event = await self._event_store.record_internal_failure(
                        service="llm",
                        message=f"LLM Service Error: {exc.summary}",
                        exception_type="LLMServiceError",
                        exception_message=exc.user_message
                    )
                    # Dispatch a critical alert to the admin group
                    await self._notifier.notify_alert(event)
                    
                    output = f"Sorry, I encountered an error: {exc.user_message}"




        await self._event_store.record_internal_event(
            service="admin-command",
            message=f"Admin command executed (is_admin={is_admin}): {command}",
            level="info",
        )
        return AdminCommandResponse(status="ok", output=output, document_path=doc_path)

