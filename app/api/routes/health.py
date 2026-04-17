from fastapi import APIRouter, Depends

from app.core.dependencies import get_health_service
from app.schemas.health import HealthResponse
from app.services.health import HealthService

router = APIRouter()


@router.get("/health/check", response_model=HealthResponse)
async def check_health(
    service: str | None = None,
    health_service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    return await health_service.check(service)
