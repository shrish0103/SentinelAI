import asyncio

import httpx

from app.core.config import Settings
from app.schemas.health import HealthResponse, ServiceHealth
from app.services.event_store import EventStore
from app.services.notifier import TelegramNotifier


class HealthService:
    def __init__(
        self,
        settings: Settings,
        notifier: TelegramNotifier,
        event_store: EventStore,
    ) -> None:
        self._settings = settings
        self._notifier = notifier
        self._event_store = event_store

    async def check(self, service: str | None = None) -> HealthResponse:
        targets = self._settings.service_targets
        names = [service] if service else list(targets.keys())
        checks = [await self._check_one(name, targets.get(name)) for name in names]
        overall_status = "ok" if all(item.status == "ok" for item in checks) else "degraded"
        return HealthResponse(status=overall_status, checks=checks)

    async def _check_one(self, service_name: str, target: str | None) -> ServiceHealth:
        if target is None:
            return ServiceHealth(service=service_name, status="unknown", detail="Service is not registered.")

        if target.startswith("telegram://"):
            return ServiceHealth(service=service_name, status="ok", detail="Telegram notifier is configured as a transport seam.")

        if target.startswith("provider://"):
            return ServiceHealth(service=service_name, status="ok", detail=f"LLM provider '{self._settings.model_provider}' is selected.")

        try:
            timeout = httpx.Timeout(self._settings.health_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(target)
            if response.is_success:
                return ServiceHealth(service=service_name, status="ok", detail=f"{target} responded with {response.status_code}.")
            result = ServiceHealth(service=service_name, status="degraded", detail=f"{target} responded with {response.status_code}.")
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            result = ServiceHealth(service=service_name, status="degraded", detail=f"{target} is unreachable: {exc}")

        failure_event = await self._event_store.record_internal_failure(
            service=service_name,
            message=result.detail,
            exception_type="HealthCheckError",
        )
        await self._notifier.notify_alert(failure_event)
        return result
