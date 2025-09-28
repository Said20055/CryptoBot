 # handlers/proxy.py

"""
Обработчики для пересылки сообщений между пользователем (через FSM)
и операторами в теме.
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import SUPPORT_GROUP_ID
from utils.logging_config import logger
from utils.database.db_helpers import get_active_order_for_user, get_order_by_topic_id
import utils.texts as texts
from utils.states import TransactionStates
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ProxyResult:
    ok: bool
    code: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


async def get_active_order_for_user_safe(user_id: int) -> ProxyResult:
    res = await get_active_order_for_user(user_id)
    if res is None:
        return ProxyResult(ok=False, code='db_error', message='DB error while fetching active order')
    return ProxyResult(ok=True, code='ok', data={'active_order': res})


async def ensure_topic_and_order(user_id: int) -> ProxyResult:
    pr = await get_active_order_for_user_safe(user_id)
    if not pr.ok:
        return pr
    active = pr.data.get('active_order')
    if not active:
        return ProxyResult(ok=True, code='ok', data={'active_order': None})
    # Do not construct or return web links to forum topics
    return ProxyResult(ok=True, code='ok', data={'active_order': active})


async def start_user_reply_prompt(callback_query, state) -> ProxyResult:
    user_id = callback_query.from_user.id
    pr = await get_active_order_for_user_safe(user_id)
    if not pr.ok:
        return pr
    active = pr.data.get('active_order')
    if not active:
        return ProxyResult(ok=False, code='no_active_order', message='No active order')
    # Set FSM state and prompt user with a persistent-reply keyboard so the session stays open
    await state.set_state(TransactionStates.waiting_for_operator_reply)
    await callback_query.message.answer(
        "✍️ Введите ваше сообщение для оператора:",
        reply_markup=texts.get_persistent_reply_keyboard()
    )
    await callback_query.answer()
    return ProxyResult(ok=True, code='ok', data={'active_order': active})


async def handle_user_message_to_topic(message, state) -> ProxyResult:
    user_id = message.from_user.id
    pr = await get_active_order_for_user_safe(user_id)
    if not pr.ok:
        await message.answer("❌ Ошибка базы данных.")
        await state.clear()
        return pr
    active = pr.data.get('active_order')
    if not active or not active.get('topic_id'):
        await message.answer("⚠️ Не удалось найти вашу активную заявку. Возможно, она уже закрыта.")
        await state.clear()
        return ProxyResult(ok=False, code='no_active_order')
    topic_id = active['topic_id']
    try:
        await message.bot.send_message(
            chat_id=SUPPORT_GROUP_ID,
            message_thread_id=topic_id,
            text=f"💬 *Сообщение от пользователя {message.from_user.full_name}:*\n\n{message.text}",
            parse_mode="Markdown"
        )
        await message.answer("✅ Ваше сообщение отправлено оператору.")
        return ProxyResult(ok=True, code='ok')
    except Exception as e:
        logger.error(f"Failed to send user message from {user_id} to topic {topic_id}: {e}")
        await message.answer("❌ Не удалось отправить сообщение. Попробуйте позже.")
        return ProxyResult(ok=False, code='send_failed', message=str(e))
    # NOTE: do not clear the FSM state here — keep the reply session active until the user
    # explicitly ends it via the "end_reply_session" callback. This allows multiple messages
    # to be sent in one session without pressing a button each time.


async def handle_operator_reply_to_user(message) -> ProxyResult:
    if not message.is_topic_message:
        return ProxyResult(ok=False, code='not_topic')
    topic_id = message.message_thread_id
    order_info = await get_order_by_topic_id(topic_id)
    if not order_info:
        return ProxyResult(ok=False, code='no_order')
    user_id = order_info.get('user_id')
    try:
        await message.copy_to(chat_id=user_id, reply_markup=texts.get_reply_to_operator_keyboard())
        return ProxyResult(ok=True, code='ok')
    except Exception as e:
        logger.error(f"Failed to proxy reply to user {user_id}: {e}")
        try:
            await message.reply(f"⚠️ Не удалось доставить сообщение пользователю {user_id}. Возможно, он заблокировал бота.")
        except Exception:
            pass
        return ProxyResult(ok=False, code='send_failed', message=str(e))

# Создаем два роутера: один для ЛС, другой для группы
private_message_router = Router()
group_message_router = Router()
group_message_router.message.filter(F.chat.id == SUPPORT_GROUP_ID)


# --- Сообщение от ПОЛЬЗОВАТЕЛЯ (в состоянии FSM) -> в ТЕМУ ---

@private_message_router.message(TransactionStates.waiting_for_operator_reply, F.chat.type == "private")
async def user_reply_to_topic_handler(message: Message, state: FSMContext):
    """
    Ловит сообщение от пользователя в состоянии ответа оператору
    и пересылает его в активную тему.
    """
    await handle_user_message_to_topic(message, state)


# --- Сообщение от ОПЕРАТОРА из ТЕМЫ -> ПОЛЬЗОВАТЕЛЮ ---

@group_message_router.message(F.chat.id == SUPPORT_GROUP_ID, F.is_topic_message == True)
async def operator_reply_to_user_handler(message: Message):
    """
    Перехватывает ответ оператора в теме и пересылает его пользователю.
    """
    if not message.is_topic_message:
        return

    await handle_operator_reply_to_user(message)


# --- Callback to end persistent reply session initiated by user ---
@private_message_router.callback_query(F.data == 'end_reply_session')
async def end_reply_session_handler(callback_query, state: FSMContext):
    """Завершает сессию переписки пользователя с операторами (очищает FSM)."""
    try:
        await state.clear()
        await callback_query.answer("✅ Переписка завершена.")
        await callback_query.message.edit_reply_markup(None)
    except Exception as e:
        logger.error(f"Error ending reply session for user {callback_query.from_user.id}: {e}")
        await callback_query.answer("Ошибка при завершении сессии.", show_alert=True)