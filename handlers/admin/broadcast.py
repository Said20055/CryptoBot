# Файл: handlers/admin/broadcast.py (НОВАЯ ВЕРСИЯ С ПОДТВЕРЖДЕНИЕМ)

import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.filters import AdminFilter
from utils.keyboards import get_broadcast_confirmation_keyboard
from utils.states import BroadcastStates
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import find_all_users
import logging

broadcast_router = Router()
broadcast_router.message.filter(AdminFilter())
broadcast_router.callback_query.filter(AdminFilter())



@broadcast_router.message(BroadcastStates.waiting_for_message)
async def broadcast_preview_handler(message: Message, state: FSMContext):
    """
    ШАГ 1: Ловит сообщение от админа, сохраняет его ID и показывает предпросмотр.
    """
    # Сохраняем ID сообщения, которое нужно будет разослать
    await state.update_data(
        message_to_broadcast_id=message.message_id,
        chat_id=message.chat.id
    )
    
    # Отправляем предпросмотр
    await message.copy_to(
        chat_id=message.chat.id,
        reply_markup=get_broadcast_confirmation_keyboard()
    )
    
    # Переводим в состояние ожидания подтверждения
    await state.set_state(BroadcastStates.waiting_for_confirmation)

@broadcast_router.callback_query(F.data == "confirm_broadcast", BroadcastStates.waiting_for_confirmation)
async def process_broadcast_confirmation(call: CallbackQuery, state: FSMContext):
    """
    ШАГ 2: После подтверждения, выполняет рассылку, используя паттерн БД.
    """
    data = await state.get_data()
    message_id = data.get('message_to_broadcast_id')
    chat_id = data.get('chat_id')
    await state.clear()

    # Убираем кнопки у сообщения с предпросмотром
    await call.message.edit_reply_markup(None)
    
    users = None
    # --- НОВЫЙ ПАТТЕРН РАБОТЫ С БД ---
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                users = await find_all_users(cursor)
    except Exception as e:
        logger.error(f"DB error during broadcast: {e}", exc_info=True)
        await call.message.answer("❌ Ошибка базы данных при получении списка пользователей.")
        return
    # --- КОНЕЦ НОВОГО ПАТТЕРНА ---

    if not users:
        await call.message.answer("Пользователи для рассылки не найдены.")
        return

    await call.answer("Начинаю рассылку...", show_alert=True)
    
    successful, failed = 0, 0
    for user in users:
        try:
            # Используем bot.copy_message для точного копирования исходного сообщения
            await call.bot.copy_message(chat_id=user[0], from_chat_id=chat_id, message_id=message_id)
            successful += 1
        except Exception as e:
            failed += 1
            logging.error(f"Failed to send broadcast to user {user[0]}: {e}")

    report = (
        f"📢 <b>Рассылка завершена.</b>\n\n"
        f"✅ Успешно отправлено: <b>{successful}</b>\n"
        f"❌ Ошибок: <b>{failed}</b>"
    )
    await call.message.answer(report, parse_mode="HTML")

@broadcast_router.callback_query(F.data == "cancel_broadcast", BroadcastStates.waiting_for_confirmation)
async def cancel_broadcast_handler(call: CallbackQuery, state: FSMContext):
    """Обрабатывает отмену рассылки на этапе подтверждения."""
    await state.clear()
    await call.message.edit_text("Рассылка отменена.")
    await call.answer()