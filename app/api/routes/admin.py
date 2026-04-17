from fastapi import APIRouter, Depends, Header, HTTPException, status

from core.dependencies import get_admin_service, get_settings
from schemas.admin import AdminCommandRequest, AdminCommandResponse
from services.admin import AdminService

router = APIRouter()


@router.post("/admin/exec", response_model=AdminCommandResponse)
async def execute_admin_command(
    payload: AdminCommandRequest,
    admin_service: AdminService = Depends(get_admin_service),
    settings=Depends(get_settings),
    x_telegram_user_id: int | None = Header(default=None),
) -> AdminCommandResponse:
    is_admin = x_telegram_user_id in settings.owner_telegram_id_set
    return await admin_service.execute(payload.command, is_admin=is_admin)
