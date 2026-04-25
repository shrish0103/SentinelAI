import asyncio
from typing import Optional

from aiogram import Bot, Dispatcher
import logging
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile
from aiogram.exceptions import TelegramAPIError

from core.dependencies import get_admin_service, load_settings

from services.admin import AdminService
from core.prompts import get_admin_help_text
from core.logger import get_logger

logger = get_logger(__name__)

import socket
from aiogram.client.session.aiohttp import AiohttpSession

dp = Dispatcher()
bot: Optional[Bot] = None

def get_bot(token: str) -> Bot:
    """Create a Bot instance with forced IPv4 session."""
    session = AiohttpSession()
    session._connector_init["family"] = socket.AF_INET
    return Bot(token=token, session=session)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    settings = load_settings()
    admin_service = get_admin_service()
    
    # Security Context Check
    is_private = message.chat.type == "private"
    is_admin_group = str(message.chat.id) == str(settings.telegram_chat_id)
    
    if not is_private and not is_admin_group:
        logger.warning(f"⚠️ Start Command Blocked: Unauthorized group {message.chat.id} ({message.chat.title})")
        await message.answer("⚠️ *Security Violation*: This bot only accepts commands via Private DM or the Admin Control Group.", parse_mode="Markdown")
        return

    is_admin = (message.from_user.id in settings.owner_telegram_id_set) if message.from_user else False
    user_id = message.from_user.id if message.from_user else 0
    
    # Use the unified executor for /start to ensure consistency
    response = await admin_service.execute("/start", is_admin=is_admin, user_id=user_id)
    try:
        await message.answer(response.output, parse_mode="Markdown")
    except TelegramAPIError:
        await message.answer(response.output)
    
    if response.document_path:
        try:
            await message.answer_document(FSInputFile(response.document_path))
        except Exception as e:
            logger.error(f"Failed to send document in start handler: {e}")



@dp.message()
async def process_message_handler(message: Message) -> None:
    settings = load_settings()
    admin_service = get_admin_service()
    
    # Security Context Check: Block commands in non-admin groups
    is_private = message.chat.type == "private"
    is_admin_group = str(message.chat.id) == str(settings.telegram_chat_id)
    
    if message.text and message.text.startswith("/") and not is_private and not is_admin_group:
        logger.warning(f"⚠️ Command Rejected: Attempt in group {message.chat.id} by user {message.from_user.id if message.from_user else 'unknown'}")
        await message.answer("⚠️ *Access Denied*: Command execution is restricted to Private DM or the official Monitoring Group.", parse_mode="Markdown")
        return

    user_id = message.from_user.id if message.from_user else 0
    is_admin = user_id in settings.owner_telegram_id_set
    
    if message.text:
        try:
            # Let AdminService decide if it's a command or a portfolio question
            response = await admin_service.execute(message.text, is_admin=is_admin, user_id=user_id)
            
            try:
                # Attempt to send with Markdown
                await message.answer(response.output, parse_mode="Markdown")
            except TelegramAPIError:
                # Fallback to plain text if Markdown parsing fails
                await message.answer(response.output)

            if response.document_path:
                try:
                    await message.answer_document(FSInputFile(response.document_path))
                except Exception as e:
                    logger.error(f"Failed to send document: {e}")

                
        except Exception as e:
            error_msg = f"⚠️ *Error*: `{str(e)}`"
            try:
                await message.answer(error_msg, parse_mode="Markdown")
            except TelegramAPIError:
                await message.answer(f"⚠️ Error: {str(e)}")


async def start_telegram_polling() -> None:
    global bot
    settings = load_settings()
    if not settings.telegram_bot_token:
        logger.warning("No TELEGRAM_BOT_TOKEN found, skipping bot polling")
        return
        
    bot = get_bot(token=settings.telegram_bot_token)
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        pass
    except TelegramAPIError as e:
        logger.error(f"Telegram API Error: {e}")

async def stop_telegram_polling() -> None:
    global bot
    if bot:
        await bot.session.close()

async def setup_webhook() -> None:
    global bot
    settings = load_settings()
    if not settings.telegram_bot_token or not settings.deploy_url:
        logger.warning("Missing bot token or deploy_url, skipping webhook setup")
        return
        
    bot = get_bot(token=settings.telegram_bot_token)
    webhook_url = f"{settings.deploy_url.rstrip('/')}/webhook"
    
    try:
        current_webhook = await bot.get_webhook_info()
        if current_webhook.url != webhook_url:
            logger.info(f"Setting Telegram Webhook to: {webhook_url}")
            await bot.set_webhook(url=webhook_url)
        else:
            logger.info(f"Telegram Webhook already set to: {webhook_url}")
    except TelegramAPIError as e:
        logger.error(f"Failed to set Telegram Webhook: {e}")
