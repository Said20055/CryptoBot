from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

import utils.admin_cache as admin_cache
from utils.database.db_helpers import acquire
from utils.database.db_queries import is_user_blocked


class BlockedUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user and not admin_cache.contains(user.id):
            async with acquire() as conn:
                if await is_user_blocked(conn, user.id):
                    if isinstance(event, Message):
                        await event.answer("🚫 Вы заблокированы в боте.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("🚫 Вы заблокированы в боте.", show_alert=True)
                    return
        return await handler(event, data)
