from fastapi import APIRouter, Request, status
from aiogram.types import Update
import logging

from services.telegram_bot import dp, bot, get_bot
from core.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook", status_code=status.HTTP_200_OK)
async def telegram_webhook(request: Request):
    """
    Handle incoming updates from Telegram via Webhook.
    """
    settings = get_settings()
    if not settings.telegram_bot_token:
        return {"status": "error", "message": "Bot token not configured"}

    # Use a global bot instance if already created, or create on the fly
    current_bot = bot or get_bot(token=settings.telegram_bot_token)
    
    try:
        # Parse the update from the request body
        update_data = await request.json()
        logger.info(f"Webhook Update Received - {update_data.get('update_id')}")
        
        update = Update(**update_data)
        
        # Feed the update to the aiogram dispatcher
        await dp.feed_update(current_bot, update)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        return {"status": "error", "message": str(e)}
