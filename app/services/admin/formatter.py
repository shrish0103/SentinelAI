from typing import List, Any
from schemas.user import UserRole
from schemas.health import HealthResponse

class AdminFormatter:
    """Handles the transformation of raw service data into user-facing Markdown UI."""
    
    @staticmethod
    def format_ping_list(targets: dict[str, str]) -> str:
        output = "🚀 *Service Registry*\n\n"
        for alias, url in targets.items():
            display_url = url.split("?")[0] if "?" in url else url
            output += f"• `{alias}`: {display_url}\n"
        output += "\n💡 _Use `/ping all` for health or `/ping <alias>` for details._"
        return output

    @staticmethod
    def format_health_report(report: HealthResponse) -> str:
        output = "🩺 *System Health Report*\n\n"
        for check in report.checks:
            status_icon = "✅" if check.status == "ok" else ("⚠️" if check.status == "degraded" else "❌")
            lat = f"({check.latency_ms}ms)" if check.latency_ms is not None else ""
            output += f"• `{check.service}`: {status_icon} {check.status.upper()} {lat}\n"
        return output

    @staticmethod
    def format_ping_detail(alias: str, check: Any, endpoint: str) -> str:
        status_icon = "✅" if check.status == "ok" else "❌"
        lat_str = f"{check.latency_ms}ms" if check.latency_ms is not None else "N/A"
        return (
            f"📡 *Health Diagnostics: {alias}*\n\n"
            f"• **Status**: {status_icon} {check.status.upper()}\n"
            f"• **Endpoint**: `{endpoint}`\n"
            f"• **Latency**: `{lat_str}`\n"
            f"• **Detail**: {check.detail or 'Healthy'}"
        )

    @staticmethod
    def format_logs(events: List[Any], limit: int) -> str:
        output = f"📋 *System Logs (Last {limit})*\n\n"
        for e in events:
            output += f"• `{e.timestamp.strftime('%H:%M:%S')}` [{e.level.upper()}] {e.service}: {e.message}\n"
        return output

    @staticmethod
    def prepend_mode_footer(output: str, role: UserRole, is_ai_mode: bool, is_undercover: bool = False) -> str:
        footers = []
        if is_undercover:
            footers.append("🕵️ _(Undercover Guest Mode active)_")
        elif role == UserRole.DEMO:
            footers.append("🎭 _(Currently in Demo Mode)_")
            
        if is_ai_mode:
            footers.append("🤖 _(General AI Mode active)_")
            
        if footers:
            output += "\n\n" + "\n".join(footers)
        return output
