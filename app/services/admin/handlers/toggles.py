from services.admin.interfaces import CommandHandler, CommandContext, CommandResult
from services.demo import DemoService
from services.admin.registry import action_registry
from core.prompts import get_admin_help_text
from core.config import Settings
from schemas.user import UserRole
import logging

logger = logging.getLogger(__name__)

@action_registry.register("demo", "ai", "guest", "admin")
class ToggleHandler(CommandHandler):
    def __init__(self, settings: Settings, demo_service: DemoService) -> None:
        self._settings = settings
        self._demo_service = demo_service

    async def handle(self, ctx: CommandContext) -> CommandResult:
        action = ctx.cmd_args[0] if ctx.cmd_args else ""
        # Default to 'on' if no action provided
        enable = action in ("", "on", "enable", "start")
        
        # --- 1. ADMIN MODE Toggle (Strict Owner Only) ---
        if ctx.intent == "admin":
            # Security Gate: Only allow if user is in the authorized owners set
            is_owner = ctx.user_id in self._settings.owner_telegram_id_set
            if not is_owner:
                 return CommandResult(success=False, message="⚠️ *Unauthorized*: Command restricted to system owner.")
            
            if enable:
                await self._demo_service.set_role(ctx.user_id, UserRole.ADMIN)
                help_text = get_admin_help_text(is_admin=True)
                return CommandResult(success=True, message=f"👑 *Admin Mode RESTORED*\n\n{help_text}")
            else:
                # Toggle off admin means dropping to guest
                await self._demo_service.set_role(ctx.user_id, UserRole.GUEST)
                help_text = get_admin_help_text(is_admin=False)
                return CommandResult(success=True, message=f"👤 *Admin Mode OFF*\n\nDropped to Guest status.\n\n{help_text}")

        # --- 2. GUEST MODE Toggle ---
        if ctx.intent == "guest":
            if enable:
                await self._demo_service.set_role(ctx.user_id, UserRole.GUEST)
                help_text = get_admin_help_text(is_admin=False)
                return CommandResult(success=True, message=f"👤 *Guest Identity ENABLED*\n\n{help_text}")
            else:
                # If they turn guest OFF, and they are the admin, they might want admin back
                # But safer to just drop to default resolution
                await self._demo_service.set_role(ctx.user_id, UserRole.GUEST) 
                return CommandResult(success=True, message="👑 Use `/admin` to restore privileges.")

        # --- 3. DEMO MODE Toggle ---
        if ctx.intent == "demo":
            if enable:
                await self._demo_service.set_role(ctx.user_id, UserRole.DEMO)
                help_text = get_admin_help_text(is_admin=True)
                return CommandResult(success=True, message=f"🎭 *Demo Mode ENABLED*\n\n{help_text}")
            else:
                await self._demo_service.set_role(ctx.user_id, UserRole.GUEST) 
                return CommandResult(success=True, message="🎭 *Demo Mode DISABLED*")
                
        # --- 4. AI MODE Toggle ---
        if ctx.intent == "ai":
            await self._demo_service.set_ai_mode(ctx.user_id, enable)
            status = "ENABLED" if enable else "DISABLED"
            emoji = "🤖" if enable else "📉"
            return CommandResult(success=True, message=f"{emoji} *General AI Mode {status}*")
                
        return CommandResult(success=False, message="❌ Invalid action.")
