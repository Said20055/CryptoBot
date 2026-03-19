# handlers/proxy.py
"""
Проксирование сообщений между пользователем (ЛС) и операторами (тема группы).
"""

from aiogram import F, Bot, Router
from aiogram.exceptions import AiogramError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import SUPPORT_GROUP_ID
from utils import keyboards
from utils.logging_config import logger
from utils.states import TransactionStates
from utils.database.db_helpers import acquire
from utils.database.db_queries import get_active_order_for_user, get_order_by_topic_id

# Два роутера: для ЛС и для группы поддержки
private_router = Router()
group_router = Router()
group_router.message.filter(F.chat.id == SUPPORT_GROUP_ID)


# =============================================================================
# --- Пользователь → тема ---
# =============================================================================

@private_router.callback_query(F.data.startswith("reply_to_"))
async def initiate_operator_reply_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    try:
        async with acquire() as conn:
            active_order = await get_active_order_for_user(conn, user_id)
    except Exception as e:
        logger.error(f"DB error in initiate_operator_reply for user {user_id}: {e}", exc_info=True)
        await callback.answer("Ошибка базы данных.", show_alert=True)
        return

    if not active_order:
        await callback.answer("⚠️ У вас нет активных заявок для ответа.", show_alert=True)
        return

    await state.set_state(TransactionStates.waiting_for_operator_reply)
    await callback.message.answer(
        "✍️ Вы вошли в режим чата с оператором. Все ваши следующие сообщения будут отправлены в вашу заявку.\n\n"
        "Чтобы выйти из этого режима, нажмите кнопку ниже.",
        reply_markup=keyboards.get_persistent_reply_keyboard(),
    )
    await callback.answer()


@private_router.message(TransactionStates.waiting_for_operator_reply, F.chat.type == "private")
async def user_message_to_topic_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        async with acquire() as conn:
            active_order = await get_active_order_for_user(conn, user_id)
    except Exception as e:
        logger.error(f"DB error in user_message_to_topic for user {user_id}: {e}", exc_info=True)
        await message.answer("❌ Ошибка базы данных.")
        return

    if not active_order or not active_order.get('topic_id'):
        await message.answer(
            "⚠️ Не удалось найти вашу активную заявку. Возможно, она уже закрыта. Вы выведены из режима чата."
        )
        await state.clear()
        return

    try:
        await message.forward(chat_id=SUPPORT_GROUP_ID, message_thread_id=active_order['topic_id'])
    except Exception as e:
        logger.error(f"Failed to forward user message from {user_id} to topic {active_order['topic_id']}: {e}")
        await message.answer("❌ Не удалось отправить сообщение. Попробуйте позже.")


@private_router.callback_query(F.data == "end_reply_session")
async def end_reply_session_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("✅ Вы вышли из режима переписки.", show_alert=True)
    try:
        await callback.message.delete()
    except AiogramError:
        pass


# =============================================================================
# --- Оператор → пользователь ---
# =============================================================================

@group_router.message(F.is_topic_message == True)
async def operator_reply_to_user_handler(message: Message, bot: Bot):
    if message.from_user.id == bot.id:
        return

    try:
        async with acquire() as conn:
            order_info = await get_order_by_topic_id(conn, message.message_thread_id)
    except Exception as e:
        logger.error(f"DB error in operator_reply for topic {message.message_thread_id}: {e}", exc_info=True)
        return

    if not order_info or not order_info.get('user_id'):
        return

    user_id = order_info['user_id']
    header = "💬 <b>Ответ от оператора:</b>\n\n"

    try:
        if message.text:
            await bot.send_message(chat_id=user_id, text=header + message.html_text, parse_mode="HTML")
        elif message.caption:
            await message.copy_to(chat_id=user_id, caption=header + message.html_caption, parse_mode="HTML")
        else:
            await bot.send_message(user_id, header, parse_mode="HTML")
            await message.copy_to(chat_id=user_id)
    except Exception as e:
        logger.error(f"Failed to proxy reply to user {user_id}: {e}", exc_info=True)
        await message.reply(
            f"⚠️ Не удалось доставить сообщение пользователю {user_id}. Возможно, он заблокировал бота."
        )
