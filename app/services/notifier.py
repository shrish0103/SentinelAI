import socket
from html import escape

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramAPIError

from app.core.config import Settings
from app.schemas.alert import EventRecord


class TelegramNotifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def notify_alert(self, event: EventRecord) -> bool:
        if not self._settings.telegram_bot_token or not self._settings.telegram_chat_id:
            return False
        session = AiohttpSession()
        session._connector_init["family"] = socket.AF_INET
        bot = Bot(token=self._settings.telegram_bot_token, session=session)
        message = self._format_message(event)
        try:
            await bot.send_message(
                chat_id=self._settings.telegram_chat_id,
                text=message,
                parse_mode="HTML",
            )
        except TelegramAPIError:
            return False
        finally:
            await bot.session.close()
        return True

    def _format_message(self, event: EventRecord) -> str:
        lines = [
            f"<b>ALERT</b>: <b>{escape(event.level.upper())}</b>",
            f"<b>App</b>: {escape(event.app_name)}",
            f"<b>Service</b>: {escape(event.service)}",
            f"<b>Summary</b>: {escape(event.message)}",
        ]
        if event.exception:
            lines.extend(
                [
                    f"<b>Exception Type</b>: <code>{escape(event.exception.type)}</code>",
                    f"<b>Exception Detail</b>: {escape(event.exception.message)}",
                ]
            )
            if event.exception.trace:
                lines.append(f"<b>Trace</b>: <code>{escape(event.exception.trace)}</code>")
        lines.extend(
            [
                f"<b>Source</b>: {escape(event.source)}",
                f"<b>Time</b>: <code>{escape(event.timestamp.isoformat())}</code>",
            ]
        )
        return "\n".join(lines)
