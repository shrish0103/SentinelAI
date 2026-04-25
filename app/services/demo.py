import httpx
import json
from typing import Dict, Any, Optional
from core.config import Settings
from core.logger import get_logger
from schemas.user import UserRole

logger = get_logger(__name__)

class DemoService:
    """
    Session-aware service using Redis Hashes to manage user personas and state.
    Key structure: user_session:{user_id} -> { role: str, ai_mode: str }
    """
    def __init__(self, settings: Settings) -> None:
        self._url = settings.upstash_redis_rest_url.rstrip("/") if settings.upstash_redis_rest_url else None
        self._token = settings.upstash_redis_rest_token
        self._ttl = 10800 # 3 hours

    async def _get_field(self, user_id: int, field: str) -> Optional[str]:
        """HGET a specific field from the user's session hash."""
        if not self._url or not self._token: return None
        try:
            async with httpx.AsyncClient() as client:
                # HGET command via Upstash REST
                res = await client.get(
                    f"{self._url}/hget/user_session:{user_id}/{field}",
                    headers={"Authorization": f"Bearer {self._token}"}
                )
                return res.json().get("result")
        except Exception as e:
            logger.error(f"Redis HGET failed", extra={"user_id": user_id, "field": field, "error": str(e)})
            return None

    async def _set_field(self, user_id: int, field: str, value: str) -> bool:
        """HSET a field and refresh TTL."""
        if not self._url or not self._token: return False
        try:
            async with httpx.AsyncClient() as client:
                # HSET + EXPIRE pipeline equivalent
                await client.get(f"{self._url}/hset/user_session:{user_id}/{field}/{value}", headers={"Authorization": f"Bearer {self._token}"})
                await client.get(f"{self._url}/expire/user_session:{user_id}/{self._ttl}", headers={"Authorization": f"Bearer {self._token}"})
            return True
        except Exception as e:
            logger.error(f"Redis HSET failed", extra={"user_id": user_id, "field": field, "error": str(e)})
            return False

    # --- Role Management ---
    async def get_role(self, user_id: int, default: UserRole = UserRole.GUEST) -> UserRole:
        role_str = await self._get_field(user_id, "role")
        try:
            return UserRole(role_str) if role_str else default
        except ValueError:
            return default

    async def set_role(self, user_id: int, role: UserRole) -> bool:
        logger.info(f"🎭 Identity Shift", extra={"user_id": user_id, "new_role": role.value})
        return await self._set_field(user_id, "role", role.value)

    # --- AI Mode (Modifier) ---
    async def is_ai_mode(self, user_id: int) -> bool:
        res = await self._get_field(user_id, "ai_mode")
        return res == "on"

    async def set_ai_mode(self, user_id: int, active: bool) -> bool:
        mode = "on" if active else "off"
        logger.info(f"🤖 AI Context Shift", extra={"user_id": user_id, "ai_mode": mode})
        return await self._set_field(user_id, "ai_mode", mode)

    # --- Backwards Compatibility for Mocking (Keeping signatures same for now) ---
    async def is_demo_user(self, user_id: int) -> bool:
        return await self.get_role(user_id) == UserRole.DEMO

    async def is_guest_mode(self, user_id: int) -> bool:
        return await self.get_role(user_id) == UserRole.GUEST

    def get_mock_logs(self, limit: int = 5) -> str:
        mock_events = [
            "• `[CRITICAL]` sentinel-api: Database connection pool exhausted (Retrying...)",
            "• `[WARNING]` llm-service: Primary provider timeout. Fallback engaged.",
            "• `[INFO]` auth-service: Admin login from California, US",
            "• `[INFO]` payment-worker: Processed 143 new transactions",
            "• `[CRITICAL]` gateway: Massive spikes in 502 Errors on /api/v1/auth",
        ]
        return "📋 *DEMO MODE: System Logs*\n\n" + "\n".join(mock_events[:limit])

    def get_mock_health_registry(self) -> str:
        return (
            "🚀 *Service Registry & Health (Demo)*\n\n"
            "• `api`: ✅ ONLINE (14ms)\n"
            "• `telegram`: ✅ ONLINE (201ms)\n"
            "• `upstash`: ✅ ONLINE (45ms)\n"
            "• `llm`: ✅ ONLINE (OpenRouter: gemma-31b)\n\n"
            "💡 _Use `/ping <alias>` for deep diagnostics._"
        )

    def get_mock_ping_detail(self, alias: str) -> str:
        data = {
            "api": ("✅ ONLINE", "https://api.sentinelai.io", "14ms", "FastAPI Core"),
            "telegram": ("✅ ONLINE", "https://api.telegram.org", "201ms", "Bot API"),
            "upstash": ("✅ ONLINE", "https://us1-standard-octopus.upstash.io", "45ms", "Redis REST"),
            "llm": ("✅ ONLINE", "https://openrouter.ai/api/v1", "882ms", "Gemma-31B-It"),
        }
        status, endpoint, latency, provider = data.get(alias.lower(), ("❓ UNKNOWN", "N/A", "N/A", "N/A"))
        return (
            f"📡 *Health Diagnostics: {alias}*\n\n"
            f"• **Status**: {status}\n"
            f"• **Endpoint**: `{endpoint}`\n"
            f"• **Latency**: `{latency}`\n"
            f"• **Provider**: `{provider}`"
        )
