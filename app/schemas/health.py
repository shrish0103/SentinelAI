from pydantic import BaseModel


class ServiceHealth(BaseModel):
    service: str
    status: str
    detail: str


class HealthResponse(BaseModel):
    status: str
    checks: list[ServiceHealth]
