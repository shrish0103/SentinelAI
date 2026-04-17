from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.dependencies import get_admin_service, get_settings
from app.schemas.admin import AdminCommandRequest, AdminCommandResponse
from app.services.admin import AdminService

router = APIRouter()


@router.post("/admin/exec", response_model=AdminCommandResponse)
async def execute_admin_command(
    payload: AdminCommandRequest,
    admin_service: AdminService = Depends(get_admin_service),
    settings=Depends(get_settings),
    x_telegram_user_id: int | None = Header(default=None),
) -> AdminCommandResponse:
    if x_telegram_user_id not in settings.owner_telegram_id_set:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access required.",
        )
    return await admin_service.execute(payload.command)
