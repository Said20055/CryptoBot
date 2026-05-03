# Файл: utils/filters.py

from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from typing import Union
import utils.admin_cache as admin_cache

class AdminFilter(Filter):
    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        return admin_cache.contains(event.from_user.id)