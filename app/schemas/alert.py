from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


Severity = Literal["info", "warning", "critical"]


class ExceptionInfo(BaseModel):
    type: str
    message: str
    trace: str | None = None


class AlertIngestRequest(BaseModel):
    app_name: str = Field(min_length=1, max_length=100)
    service: str = Field(min_length=1, max_length=100)
    level: Severity
    message: str = Field(min_length=1, max_length=500)
    exception: ExceptionInfo | None = None


class EventRecord(AlertIngestRequest):
    id: str
    timestamp: datetime
    source: Literal["external", "internal"] = "external"

    @classmethod
    def from_alert(cls, payload: AlertIngestRequest) -> "EventRecord":
        return cls(
            **payload.model_dump(),
            id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            source="external",
        )


class AlertResponse(BaseModel):
    status: Literal["accepted"]
    event: EventRecord
