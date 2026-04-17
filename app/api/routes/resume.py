from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_event_store, get_llm_service, get_notifier
from app.schemas.resume import ResumeAnswer, ResumeQuestion
from app.services.event_store import EventStore
from app.services.llm import LLMService, LLMServiceError
from app.services.notifier import TelegramNotifier

router = APIRouter()


@router.post("/resume/ask", response_model=ResumeAnswer)
async def ask_resume_question(
    payload: ResumeQuestion,
    llm_service: LLMService = Depends(get_llm_service),
    event_store: EventStore = Depends(get_event_store),
    notifier: TelegramNotifier = Depends(get_notifier),
) -> ResumeAnswer:
    try:
        answer = await llm_service.answer_question(payload.question)
    except LLMServiceError as exc:
        failure_event = await event_store.record_internal_failure(
            service="llm-provider",
            message=f"Resume assistant request failed via {exc.summary}.",
            exception_type=exc.__class__.__name__,
            exception_message=exc.user_message,
        )
        await notifier.notify_alert(failure_event)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider unavailable. Retry shortly.",
        ) from exc

    return ResumeAnswer(
        answer=answer,
        provider=llm_service.provider_name,
        used_fallback=llm_service.using_fallback,
    )
