"""
Middleware для логирования входящих запросов.

Логирует user_id, тип события и время обработки хендлера.
"""

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from utils.logging_config import logger


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        action = ""

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            action = f"message: {event.text[:50] if event.text else '[media]'}"
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            action = f"callback: {event.data}"

        start = time.monotonic()
        result = await handler(event, data)
        elapsed = (time.monotonic() - start) * 1000

        logger.debug(f"user={user_id} | {action} | {elapsed:.1f}ms")
        return result
