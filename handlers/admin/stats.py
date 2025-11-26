from asyncio.log import logger
from aiogram import Router
import aiosqlite
from aiogram.exceptions import AiogramError
from aiogram import F
from aiogram.types import CallbackQuery
from config import REFERRAL_PERCENTAGE
from utils import keyboards, texts
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import get_admin_statistics


stats_router = Router()



@stats_router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    """Собирает и отправляет статистику."""
    stats_data = {}
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                stats_data = await get_admin_statistics(cursor)
    except Exception as e:
        logger.error(f"DB error in admin_stats_handler: {e}", exc_info=True)
        await callback.answer("Ошибка базы данных при сборе статистики!", show_alert=True)
        return

    # Формируем текст сообщения со статистикой
    text = texts.get_statistics_text(stats_data)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = keyboards.back_to_admin_panel()
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()