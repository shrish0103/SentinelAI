from services.admin.interfaces import CommandHandler, CommandContext, CommandResult
from services.admin.formatter import AdminFormatter
from services.health import HealthService
from core.config import Settings
from services.admin.registry import action_registry
from services.demo import DemoService
from schemas.user import UserRole

@action_registry.register("ping", "check")
class DiagnosticsHandler(CommandHandler):
    def __init__(self, settings: Settings, health_service: HealthService, demo_service: DemoService) -> None:
        self._settings = settings
        self._health_service = health_service
        self._demo_service = demo_service

    async def handle(self, ctx: CommandContext) -> CommandResult:
        formatter = AdminFormatter()
        
        # Branch 1: List Services (Mock if Demo)
        if not ctx.cmd_args:
            if ctx.role == UserRole.DEMO:
                return CommandResult(success=True, data=None, message=self._demo_service.get_mock_health_registry())
            
            return CommandResult(
                success=True, 
                data=self._settings.service_targets,
                message=formatter.format_ping_list(self._settings.service_targets)
            )
            
        alias = ctx.cmd_args[0]
        
        # Branch 2: Full Health Check (Mock if Demo)
        if alias == "all":
            if ctx.role == UserRole.DEMO:
                return CommandResult(success=True, data=None, message=self._demo_service.get_mock_health_registry())
                
            report = await self._health_service.check()
            return CommandResult(
                success=True,
                data=report,
                message=formatter.format_health_report(report)
            )
            
        # Branch 3: Deep Diagnostic (Mock if Demo)
        if ctx.role == UserRole.DEMO:
            return CommandResult(success=True, data=None, message=self._demo_service.get_mock_ping_detail(alias))
            
        health = await self._health_service.check(alias)
        if not health.checks:
            return CommandResult(success=False, data=None, message=f"❌ Service `{alias}` not found.")
            
        check = health.checks[0]
        endpoint = self._settings.service_targets.get(alias, "N/A")
        return CommandResult(
            success=True,
            data=check,
            message=formatter.format_ping_detail(alias, check, endpoint)
        )
