import asyncio
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError

from core.dependencies import get_admin_service, load_settings

dp = Dispatcher()
bot: Optional[Bot] = None

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    settings = load_settings()
    if message.from_user is None or message.from_user.id not in settings.owner_telegram_id_set:
        await message.answer("Hello! This is a private SentinelAI instance.")
        return
        
    await message.answer(
        "<b>SentinelAI is active.</b>\n\n"
        "Send me an admin command:\n"
        "• <code>ping</code>\n"
        "• <code>logs</code>\n"
        "• <code>check &lt;service&gt;</code>",
        parse_mode="HTML"
    )

@dp.message()
async def process_admin_command(message: Message) -> None:
    settings = load_settings()
    if message.from_user is None or message.from_user.id not in settings.owner_telegram_id_set:
        await message.answer("Unauthorized.")
        return
    
    admin_service = get_admin_service()
    if message.text:
        try:
            response = await admin_service.execute(message.text)
            await message.answer(f"<pre>{response.output}</pre>", parse_mode="HTML")
        except Exception as e:
            await message.answer(f"<b>Error executing command</b>:\n<code>{str(e)}</code>", parse_mode="HTML")

async def start_telegram_polling() -> None:
    global bot
    settings = load_settings()
    if not settings.telegram_bot_token:
        print("No TELEGRAM_BOT_TOKEN found, skipping bot polling")
        return
        
    bot = Bot(token=settings.telegram_bot_token)
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        pass
    except TelegramAPIError as e:
        print(f"Telegram API Error: {e}")

async def stop_telegram_polling() -> None:
    global bot
    if bot:
        await bot.session.close()
