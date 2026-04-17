from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_event_store
from app.schemas.log import LogListResponse
from app.services.event_store import EventStore

router = APIRouter()


@router.get("/logs", response_model=LogListResponse)
async def list_logs(
    limit: int = Query(default=50, ge=1, le=200),
    level: str | None = Query(default=None),
    event_store: EventStore = Depends(get_event_store),
) -> LogListResponse:
    events = await event_store.list_events(limit=limit, level=level)
    return LogListResponse(total=len(events), items=events)
