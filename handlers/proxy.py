# handlers/proxy.py (НОВАЯ, УЛУЧШЕННАЯ ВЕРСИЯ)

"""
Обработчики для пересылки сообщений между пользователем (через FSM)
и операторами в теме.
Логика основана на рабочем примере системы поддержки.
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import AiogramError

from config import SUPPORT_GROUP_ID
from utils.logging_config import logger
from utils.database.db_helpers import get_active_order_for_user, get_order_by_topic_id
import utils.texts as texts
from utils.states import TransactionStates

# --- РОУТЕРЫ ---
# Создаем два роутера, как и раньше: один для ЛС, другой для группы
private_message_router = Router()
group_message_router = Router()
# Сразу применяем фильтр на ID группы ко всем хендлерам в этом роутере
group_message_router.message.filter(F.chat.id == SUPPORT_GROUP_ID)


# =============================================================================
# --- ЛОГИКА ДЛЯ ПОЛЬЗОВАТЕЛЯ (ВХОД В ЧАТ И ОТПРАВКА СООБЩЕНИЙ) ---
# =============================================================================

@private_message_router.callback_query(F.data.startswith('reply_to_'))
async def initiate_operator_reply_handler(callback_query: CallbackQuery, state: FSMContext):
    """
    Инициирует сессию переписки с оператором.
    Срабатывает на кнопки 'reply_to_active_order' и 'reply_to_operator'.
    """
    user_id = callback_query.from_user.id
    active_order = await get_active_order_for_user(user_id)

    if not active_order:
        await callback_query.answer("⚠️ У вас нет активных заявок для ответа.", show_alert=True)
        return

    # Устанавливаем состояние и показываем клавиатуру для завершения диалога
    await state.set_state(TransactionStates.waiting_for_operator_reply)
    await callback_query.message.answer(
        "✍️ Вы вошли в режим чата с оператором. Все ваши следующие сообщения будут отправлены в вашу заявку.\n\n"
        "Чтобы выйти из этого режима, нажмите кнопку ниже.",
        reply_markup=texts.get_persistent_reply_keyboard() # Клавиатура с кнопкой "Завершить диалог"
    )
    await callback_query.answer()


@private_message_router.message(TransactionStates.waiting_for_operator_reply, F.chat.type == "private")
async def user_message_to_topic_handler(message: Message, state: FSMContext):
    """
    Ловит сообщение от пользователя в состоянии чата и ПЕРЕСЫЛАЕТ его в тему.
    Используем message.forward() как в примере, чтобы оператор видел, от кого сообщение.
    """
    user_id = message.from_user.id
    active_order = await get_active_order_for_user(user_id)

    if not active_order or not active_order.get('topic_id'):
        await message.answer("⚠️ Не удалось найти вашу активную заявку. Возможно, она уже закрыта. Вы выведены из режима чата.")
        await state.clear()
        return

    topic_id = active_order['topic_id']
    try:
        # Используем forward для сохранения авторства сообщения
        await message.forward(
            chat_id=SUPPORT_GROUP_ID,
            message_thread_id=topic_id
        )
    except Exception as e:
        logger.error(f"Failed to forward user message from {user_id} to topic {topic_id}: {e}")
        await message.answer("❌ Не удалось отправить сообщение. Попробуйте позже.")


@private_message_router.callback_query(F.data == 'end_reply_session')
async def end_reply_session_handler(callback_query: CallbackQuery, state: FSMContext):
    """Завершает сессию переписки пользователя с операторами (очищает FSM)."""
    await state.clear()
    await callback_query.answer("✅ Вы вышли из режима переписки.", show_alert=True)
    try:
        # Удаляем сообщение с кнопкой "Завершить диалог"
        await callback_query.message.delete()
    except AiogramError:
        pass


# =============================================================================
# --- ЛОГИКА ДЛЯ ОПЕРАТОРА (ОТВЕТ ИЗ ТЕМЫ ПОЛЬЗОВАТЕЛЮ) ---
# =============================================================================

@group_message_router.message(F.is_topic_message == True)
async def operator_reply_to_user_handler(message: Message, bot: Bot):
    """
    Перехватывает ответ оператора в теме и пересылает его пользователю.
    Логика полностью адаптирована из рабочего примера.
    """
    # Игнорируем сообщения от самого бота (служебные уведомления и т.д.)
    if message.from_user.id == bot.id:
        return

    # Ищем заявку (и пользователя) по ID темы, в которой написано сообщение
    order_info = await get_order_by_topic_id(message.message_thread_id)
    if not order_info or not order_info.get('user_id'):
        # Если заявка не найдена, ничего не делаем. Это может быть системное сообщение.
        return

    user_id = order_info.get('user_id')
    header = "💬 <b>Ответ от оператора:</b>\n\n" # "Шапка", как в примере

    try:
        # 1. Если оператор отправил только текст
        if message.text:
            await bot.send_message(
                chat_id=user_id,
                text=header + message.html_text, # Используем html_text для сохранения форматирования
                parse_mode="HTML"
            )
        # 2. Если оператор отправил медиа с подписью (caption)
        elif message.caption:
            await message.copy_to(
                chat_id=user_id,
                caption=header + message.html_captio,
                parse_mode="HTML"
                
            )
        # 3. Если оператор отправил медиа БЕЗ подписи
        else:
            # Сначала отправляем "шапку"
            await bot.send_message(user_id, header)
            # Затем копируем медиафайл
            await message.copy_to(
                chat_id=user_id,
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Failed to proxy reply to user {user_id}: {e}", exc_info=True)
        # Если не удалось отправить, отвечаем оператору в тему, как в примере
        await message.reply(f"⚠️ Не удалось доставить сообщение пользователю {user_id}. Возможно, он заблокировал бота.")