from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4
import asyncio

from schemas.alert import EventRecord, ExceptionInfo


class EventStore:
    def __init__(self) -> None:
        self._events: list[EventRecord] = []
        self._lock = asyncio.Lock()

    async def append(self, event: EventRecord) -> EventRecord:
        async with self._lock:
            self._events.append(event)
        return event

    async def list_events(self, limit: int = 50, level: str | None = None) -> list[EventRecord]:
        async with self._lock:
            events: Iterable[EventRecord] = reversed(self._events)
            if level:
                events = (event for event in events if event.level == level)
            return list(events)[:limit]

    async def record_internal_failure(
        self,
        service: str,
        message: str,
        exception_type: str,
        exception_message: str | None = None,
        trace: str | None = None,
    ) -> EventRecord:
        event = EventRecord(
            id=str(uuid4()),
            app_name="sentinel-ai",
            service=service,
            level="critical",
            message=message,
            exception=ExceptionInfo(
                type=exception_type,
                message=exception_message or message,
                trace=trace,
            ),
            timestamp=datetime.now(timezone.utc),
            source="internal",
        )
        return await self.append(event)

    async def record_internal_event(
        self,
        service: str,
        message: str,
        level: str = "info",
    ) -> EventRecord:
        event = EventRecord(
            id=str(uuid4()),
            app_name="sentinel-ai",
            service=service,
            level=level,
            message=message,
            exception=None,
            timestamp=datetime.now(timezone.utc),
            source="internal",
        )
        return await self.append(event)
