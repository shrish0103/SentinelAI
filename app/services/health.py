import asyncio
import time
import httpx
from core.config import Settings
from schemas.health import HealthResponse, ServiceHealth
from services.event_store import EventStore
from services.notifier import TelegramNotifier
from core.logger import get_logger

logger = get_logger(__name__)

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
        
        logger.info(
            f"📋 Initiating health registry check", 
            extra={"services": names, "target_count": len(names)}
        )
        checks = [await self._check_one(name, targets.get(name)) for name in names]
        
        all_ok = all(c.status == "ok" for c in checks)
        status_text = "HEALTHY" if all_ok else "DEGRADED"
        logger.info(
            f"🏁 Health check execution finished", 
            extra={"system_status": status_text, "ok_count": sum(1 for c in checks if c.status == "ok")}
        )
        
        return HealthResponse(
            status="healthy" if all_ok else "unhealthy",
            checks=checks
        )

    async def _check_one(self, service_name: str, target: str | None) -> ServiceHealth:
        if target is None:
            logger.warning(
                f"❓ Service not registered", 
                extra={"service": service_name}
            )
            return ServiceHealth(service=service_name, status="unknown", detail="Service is not registered.")

        start_time = time.perf_counter()

        if target.startswith("telegram://"):
            logger.info(
                f"📡 Verifying Telegram transport seam", 
                extra={"service": service_name, "transport": "aiogram"}
            )
            return ServiceHealth(service=service_name, status="ok", detail="Telegram bot layer is configured.")

        # REAL LLM PING (OpenRouter)
        if target.startswith("provider://") or service_name == "llm":
            logger.info(
                f"🧠 Validating LLM connectivity", 
                extra={"service": service_name, "provider": self._settings.model_provider}
            )
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://openrouter.ai/api/v1/models",
                        headers={"Authorization": f"Bearer {self._settings.api_key}"},
                        timeout=5.0
                    )
                latency = int((time.perf_counter() - start_time) * 1000)
                if response.status_code == 200:
                    logger.info(
                        f"✅ LLM connectivity successful", 
                        extra={"service": service_name, "latency_ms": latency}
                    )
                    return ServiceHealth(service=service_name, status="ok", detail=f"LLM Provider is active.", latency_ms=latency)
                
                logger.error(
                    f"❌ LLM Auth failure", 
                    extra={"service": service_name, "status_code": response.status_code, "latency_ms": latency}
                )
                return ServiceHealth(service=service_name, status="degraded", detail=f"LLM Error: {response.status_code}", latency_ms=latency)
            except Exception as e:
                logger.error(
                    f"❌ LLM Connectivity exception", 
                    extra={"service": service_name, "error": str(e)}
                )
                return ServiceHealth(service=service_name, status="degraded", detail=f"LLM Error: {str(e)}")

        if target.startswith("redis://rest"):
            url = self._settings.upstash_redis_rest_url
            logger.info(
                f"🗄️ Verifying Redis persistence", 
                extra={"service": service_name, "endpoint": url}
            )
            ping_url = f"{url.rstrip('/')}/ping"
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(ping_url, headers={"Authorization": f"Bearer {self._settings.upstash_redis_rest_token}"})
                latency = int((time.perf_counter() - start_time) * 1000)
                if response.status_code == 200:
                    logger.info(
                        f"✅ Redis health check successful", 
                        extra={"service": service_name, "latency_ms": latency}
                    )
                    return ServiceHealth(service=service_name, status="ok", detail="Upstash Redis is responsive.", latency_ms=latency)
                
                logger.warning(
                    f"❌ Redis health check degraded", 
                    extra={"service": service_name, "status_code": response.status_code, "latency_ms": latency}
                )
                return ServiceHealth(service=service_name, status="degraded", detail=f"Upstash Error: {response.status_code}", latency_ms=latency)
            except Exception as e:
                logger.error(
                    f"❌ Redis connectivity exception", 
                    extra={"service": service_name, "error": str(e)}
                )
                return ServiceHealth(service=service_name, status="degraded", detail=f"Connection failed: {str(e)}")

        # Generic HTTP Targets
        logger.info(
            f"🌐 Probing HTTP service", 
            extra={"service": service_name, "url": target}
        )
        try:
            timeout = httpx.Timeout(self._settings.health_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(target)
            latency = int((time.perf_counter() - start_time) * 1000)
            if response.is_success:
                logger.info(
                    f"✅ HTTP probe successful", 
                    extra={"service": service_name, "latency_ms": latency}
                )
                return ServiceHealth(service=service_name, status="ok", detail=f"Ping successful.", latency_ms=latency)
            
            logger.warning(
                f"❌ HTTP probe failed", 
                extra={"service": service_name, "status_code": response.status_code, "latency_ms": latency}
            )
            return ServiceHealth(service=service_name, status="degraded", detail=f"Target responded with {response.status_code}.", latency_ms=latency)
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            logger.error(
                f"❌ HTTP connectivity unreachable", 
                extra={"service": service_name, "error": str(exc)}
            )
            return ServiceHealth(service=service_name, status="degraded", detail=f"Target is unreachable: {exc}")
