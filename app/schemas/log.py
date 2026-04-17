from pydantic import BaseModel

from schemas.alert import EventRecord


class LogListResponse(BaseModel):
    total: int
    items: list[EventRecord]
