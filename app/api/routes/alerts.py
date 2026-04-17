from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.core.dependencies import get_event_store, get_notifier
from app.schemas.alert import AlertIngestRequest, AlertResponse, EventRecord
from app.services.event_store import EventStore
from app.services.notifier import TelegramNotifier

router = APIRouter()


@router.post(
    "/alert",
    response_model=AlertResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_alert(
    payload: AlertIngestRequest,
    background_tasks: BackgroundTasks,
    event_store: EventStore = Depends(get_event_store),
    notifier: TelegramNotifier = Depends(get_notifier),
) -> AlertResponse:
    event = EventRecord.from_alert(payload)
    stored_event = await event_store.append(event)
    background_tasks.add_task(notifier.notify_alert, stored_event)
    return AlertResponse(status="accepted", event=stored_event)
