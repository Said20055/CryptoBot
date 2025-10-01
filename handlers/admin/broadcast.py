# Файл: handlers/admin/broadcast.py
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from utils.filters import AdminFilter
from utils.states import BroadcastStates
from utils.database.db_queries import find_all_users
from config import ADMIN_CHAT_ID

broadcast_router = Router()
broadcast_router.message.filter(AdminFilter()) # Защищаем FSM-хендлер

@broadcast_router.message(BroadcastStates.waiting_for_message)
async def broadcast_message_handler(message: Message, state: FSMContext):
    """Обрабатывает получение сообщения и выполняет рассылку."""
    await state.clear()
    users = await find_all_users()
    if not users:
        await message.answer("Пользователи для рассылки не найдены.")
        return

    successful, failed = 0, 0
    for user in users:
        try:
            # message.copy_to() - универсальный способ для пересылки любого контента
            await message.copy_to(chat_id=user[0])
            successful += 1
        except Exception as e:
            failed += 1
            logging.error(f"Failed to send broadcast to user {user[0]}: {e}")

    report = (
        f"📢 <b>Рассылка завершена.</b>\n\n"
        f"✅ Успешно отправлено: <b>{successful}</b>\n"
        f"❌ Ошибок: <b>{failed}</b>"
    )
    await message.answer(report, parse_mode="HTML")