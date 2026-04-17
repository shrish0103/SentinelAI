from pydantic import BaseModel

from app.schemas.alert import EventRecord


class LogListResponse(BaseModel):
    total: int
    items: list[EventRecord]
