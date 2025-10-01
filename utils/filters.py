# Файл: utils/filters.py

from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from typing import Union
from config import ADMIN_CHAT_ID

class AdminFilter(Filter):
    """
    Проверяет, является ли пользователь администратором.
    """
    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        return event.from_user.id in ADMIN_CHAT_ID