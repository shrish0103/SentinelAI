from pydantic import BaseModel


class ServiceHealth(BaseModel):
    service: str
    status: str
    detail: str
    latency_ms: int | None = None


class HealthResponse(BaseModel):
    status: str
    checks: list[ServiceHealth]
