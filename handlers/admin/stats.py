from aiogram import Router, F
from aiogram.types import CallbackQuery

from utils import keyboards, texts
from utils.filters import AdminFilter
from utils.logging_config import logger
from utils.database.db_helpers import acquire
from utils.database.db_queries import get_admin_statistics

router = Router()
router.callback_query.filter(AdminFilter())


@router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    """Собирает и отправляет статистику."""
    try:
        async with acquire() as conn:
            stats_data = await get_admin_statistics(conn)
    except Exception as e:
        logger.error(f"DB error in admin_stats_handler: {e}", exc_info=True)
        await callback.answer("Ошибка базы данных при сборе статистики!", show_alert=True)
        return

    text = texts.get_statistics_text(stats_data)
    keyboard = keyboards.back_to_admin_panel()
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()
