import logging
from typing import Dict, Any, Type
from core.config import Settings
from services.health import HealthService
from services.event_store import EventStore
from services.notifier import TelegramNotifier
from services.demo import DemoService
from services.admin.interfaces import CommandContext, CommandResult, LLMServiceProtocol, CommandHandler
from services.admin.parser import CommandParser
from services.admin.formatter import AdminFormatter
from services.admin.registry import action_registry
from schemas.user import UserRole
from core.logger import get_logger

# Import handlers to trigger self-registration
import services.admin.handlers.diagnostics 
import services.admin.handlers.system
import services.admin.handlers.toggles
import services.admin.handlers.portfolio

logger = get_logger(__name__)

class AdminRouter:
    """
    The orchestrator that discovers registered handlers and dispatches 
    parsed commands dynamically.
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
        self._settings = settings
        self._demo_service = demo_service
        self._llm_service = llm_service
        self._formatter = AdminFormatter()
        
        # Dependency Map for instance injection
        dep_map = {
            Settings: settings,
            HealthService: health_service,
            EventStore: event_store,
            TelegramNotifier: notifier,
            DemoService: demo_service
        }
        
        # Instantiate registered handlers dynamically
        self._handlers: Dict[str, CommandHandler] = {}
        for intent, handler_cls in action_registry.get_handler_classes().items():
            self._handlers[intent] = self._instantiate_handler(handler_cls, dep_map)
            
        logger.info(f"🦾 Router Initialized - Registered Intents: {list(self._handlers.keys())}")

    def _instantiate_handler(self, cls: Type[CommandHandler], deps: Dict[Type, Any]) -> CommandHandler:
        """Injects required dependencies into the handler constructor."""
        import inspect
        params = inspect.signature(cls.__init__).parameters
        kwargs = {}
        for name, param in params.items():
            if name == "self": continue
            if param.annotation in deps:
                kwargs[name] = deps[param.annotation]
        
        logger.debug(f"🛠️ Instantiating {cls.__name__}", extra={"deps": list(kwargs.keys())})
        return cls(**kwargs)

    async def _resolve_role(self, is_admin_context: bool, user_id: int) -> UserRole:
        # 1. Native Detection (System Preference)
        native_role = UserRole.ADMIN if is_admin_context else UserRole.GUEST
        
        # 2. Session Override (Redis Hash Source of Truth)
        # This will return the stored role (demo, guest, admin) or fallback to native
        return await self._demo_service.get_role(user_id, default=native_role)

    async def dispatch(self, raw_command: str, is_admin_context: bool = False, user_id: int = 0) -> Dict[str, Any]:
        intent, args = CommandParser.parse(raw_command)
        is_undercover = await self._demo_service.is_guest_mode(user_id)
        role = await self._resolve_role(is_admin_context, user_id)
        is_ai_mode = await self._demo_service.is_ai_mode(user_id)
        
        ctx = CommandContext(
            raw_command=raw_command,
            intent=intent,
            cmd_args=args,
            user_id=user_id,
            role=role,
            is_ai_mode=is_ai_mode
        )
        
        logger.info(f"📥 Dispatching intent '{intent}'", extra=ctx.model_dump())
        
        # Security Guard
        ADMIN_ONLY_INTENTS = {"ping", "logs", "test", "admin"}
        if intent in ADMIN_ONLY_INTENTS and role == UserRole.GUEST:
            logger.warning("🛑 Security block: Unauthorized guest access", extra=ctx.model_dump())
            return {"status": "forbidden", "output": "⚠️ Security Violation : Access Denied."}
            
        # Route to Handler
        handler = self._handlers.get(intent)
        if handler:
            result = await handler.handle(ctx)
            final_output = self._formatter.prepend_mode_footer(result.message, role, is_ai_mode, is_undercover)
            return {
                "status": "ok" if result.success else "error",
                "output": final_output,
                "document_path": result.document_path
            }
            
        # Fallback to Portfolio AI
        return await self._handle_fallback(ctx)

    async def _handle_fallback(self, ctx: CommandContext) -> Dict[str, Any]:
        from core.prompts import get_admin_help_text
        import os
        
        intent = ctx.intent
        is_undercover = await self._demo_service.is_guest_mode(ctx.user_id)

        # SECURITY FAIL-SAFE: Ensure identity toggles never reach LLM
        IDENTITY_INTENTS = ("guest", "demo", "ai", "admin")
        if intent in IDENTITY_INTENTS:
            handler = self._handlers.get("admin") # Any identity intent uses ToggleHandler
            if handler:
                result = await handler.handle(ctx)
                final_output = self._formatter.prepend_mode_footer(result.message, ctx.role, ctx.is_ai_mode, is_undercover)
                return {"status": "ok", "output": final_output}

        # Admin Admin-Commands (Meta Commands)
        if intent == "admin" and ctx.role == UserRole.ADMIN:
            arg = ctx.cmd_args[0] if ctx.cmd_args else ""
            if arg == "guest":
                logger.info("👤 [ADMIN] Previewing Guest Mode", extra={"user_id": ctx.user_id})
                guest_output = get_admin_help_text(is_admin=False)
                return {"status": "ok", "output": f"👀 *Guest View Preview*\n\n{guest_output}"}
            else:
                # Default /admin behavior: Show dashboard
                output = get_admin_help_text(is_admin=True)
                return {"status": "ok", "output": output}

        if intent in ("start", "help"):
            output = get_admin_help_text(ctx.role == UserRole.ADMIN)
        elif intent == "resume":
            output = "📄 *Shrish Gupta's Resume (2024-25)*\n\nRetrieving profile..."
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            target_pdf = os.path.join(base_dir, "app", "resume.pdf")
            return {"status": "ok", "output": output, "document_path": target_pdf if os.path.exists(target_pdf) else None}
        else:
            try:
                method = self._llm_service.answer_general_question if ctx.is_ai_mode else self._llm_service.answer_question
                output, model, _ = await method(ctx.raw_command)
                logger.info("🤖 AI response generated", extra={"model": model})
            except Exception as e:
                logger.error(f"❌ LLM error: {e}")
                output = "⚠️ Brain offline. Check /ping all."
                
        final_output = self._formatter.prepend_mode_footer(output, ctx.role, ctx.is_ai_mode, is_undercover)
        return {"status": "ok", "output": final_output}
