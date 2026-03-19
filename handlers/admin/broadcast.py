# handlers/admin/broadcast.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from utils.filters import AdminFilter
from utils.keyboards import get_broadcast_confirmation_keyboard
from utils.states import BroadcastStates
from utils.database.db_helpers import acquire
from utils.database.db_queries import find_all_users
from utils.logging_config import logger

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(BroadcastStates.waiting_for_message)
async def broadcast_preview_handler(message: Message, state: FSMContext):
    """ШАГ 1: Ловит сообщение от админа, сохраняет его ID и показывает предпросмотр."""
    await state.update_data(
        message_to_broadcast_id=message.message_id,
        chat_id=message.chat.id
    )
    await message.copy_to(
        chat_id=message.chat.id,
        reply_markup=get_broadcast_confirmation_keyboard()
    )
    await state.set_state(BroadcastStates.waiting_for_confirmation)


@router.callback_query(F.data == "confirm_broadcast", BroadcastStates.waiting_for_confirmation)
async def process_broadcast_confirmation(call: CallbackQuery, state: FSMContext):
    """ШАГ 2: После подтверждения выполняет рассылку."""
    data = await state.get_data()
    message_id = data.get('message_to_broadcast_id')
    chat_id = data.get('chat_id')
    await state.clear()

    await call.message.edit_reply_markup(None)

    try:
        async with acquire() as conn:
            users = await find_all_users(conn)
    except Exception as e:
        logger.error(f"DB error during broadcast: {e}", exc_info=True)
        await call.message.answer("❌ Ошибка базы данных при получении списка пользователей.")
        return

    if not users:
        await call.message.answer("Пользователи для рассылки не найдены.")
        return

    await call.answer("Начинаю рассылку...", show_alert=True)

    successful, failed = 0, 0
    for user in users:
        try:
            await call.bot.copy_message(chat_id=user['user_id'], from_chat_id=chat_id, message_id=message_id)
            successful += 1
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send broadcast to user {user['user_id']}: {e}")

    report = (
        f"📢 <b>Рассылка завершена.</b>\n\n"
        f"✅ Успешно отправлено: <b>{successful}</b>\n"
        f"❌ Ошибок: <b>{failed}</b>"
    )
    await call.message.answer(report, parse_mode="HTML")


@router.callback_query(F.data == "cancel_broadcast", BroadcastStates.waiting_for_confirmation)
async def cancel_broadcast_handler(call: CallbackQuery, state: FSMContext):
    """Обрабатывает отмену рассылки."""
    await state.clear()
    await call.message.edit_text("Рассылка отменена.")
    await call.answer()
