"""
Middleware для ограничения частоты запросов (anti-spam).

Разрешает не более 1 сообщения в секунду на пользователя.
При превышении лимита тихо игнорирует запрос.
"""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message
from cachetools import TTLCache


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate: float = 1.0):
        """
        :param rate: минимальный интервал между сообщениями в секундах (по умолчанию 1.0 с).
        """
        # TTLCache: ключ — user_id, значение — True, TTL = rate секунд
        self._cache: TTLCache = TTLCache(maxsize=10_000, ttl=rate)

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id if event.from_user else None
        if user_id is not None:
            if user_id in self._cache:
                # Слишком быстро — игнорируем
                return
            self._cache[user_id] = True
        return await handler(event, data)
