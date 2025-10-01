import aiosqlite

from aiogram import F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import AiogramError

from config import SUPPORT_GROUP_ID, SERVICE_COMMISSION_PERCENT, NETWORK_FEE_RUB, CRYPTO_WALLETS, SBP_PHONE, SBP_BANK
from utils.logging_config import logger
from utils.states import TransactionStates
from utils.callbacks import CryptoSelection, RubInputSwitch
from utils.crypto_rates import crypto_rates
import utils.texts as texts
import utils.keyboards as keyboards
from handlers.router import crypto_router as router

# Импортируем из файлов базы данных
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import (
    get_order_by_id, get_all_settings, get_user_activated_promo, create_order, clear_user_activated_promo,
    update_order_status, refund_promo_if_needed
)
from utils.database.db_helpers import get_active_order_for_user

# --- Блок навигации и выбора ---

@router.callback_query(F.data == 'sell')
async def sell_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора продажи криптовалюты."""
    await state.clear()
    keyboard = keyboards.get_crypto_selection_keyboard("sell")
    try:
        await callback_query.message.edit_text(texts.SELL_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="HTML")
    except AiogramError:
        await callback_query.message.delete()
        await callback_query.message.answer(texts.SELL_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="HTML")
    await callback_query.answer()

@router.callback_query(F.data == 'buy')
async def buy_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора покупки криптовалюты."""
    await state.clear()
    keyboard = keyboards.get_crypto_selection_keyboard("buy")
    try:
        await callback_query.message.edit_text(texts.BUY_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="HTML")
    except AiogramError:
        await callback_query.message.delete()
        await callback_query.message.answer(texts.BUY_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="HTML")
    await callback_query.answer()

@router.callback_query(CryptoSelection.filter())
async def select_crypto_handler(callback_query: CallbackQuery, callback_data: CryptoSelection, state: FSMContext):
    action = callback_data.action
    crypto = callback_data.crypto
    rate = await crypto_rates.get_rate(crypto)
    if not rate:
        await callback_query.answer(f"Не удалось получить курс {crypto}, попробуйте позже.", show_alert=True)
        return

    await state.update_data(action=action, crypto=crypto)
    await state.set_state(TransactionStates.waiting_for_crypto_amount)

    text = texts.get_crypto_prompt_text(action, crypto, rate)
    keyboard = keyboards.get_crypto_details_keyboard(action, crypto)

    msg = await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    # сохраняем id сообщения бота
    await state.update_data(last_bot_message_id=msg.message_id)
    await callback_query.answer()

@router.callback_query(RubInputSwitch.filter())
async def switch_to_rub_input_handler(callback_query: CallbackQuery, callback_data: RubInputSwitch, state: FSMContext):
    """Универсальный обработчик переключения на ввод в рублях."""
    action = callback_data.action
    crypto = callback_data.crypto
    rate = await crypto_rates.get_rate(crypto)
    if not rate:
        await callback_query.answer(f"Не удалось получить курс {crypto}, попробуйте позже.", show_alert=True)
        return
    await state.set_state(TransactionStates.waiting_for_rub_amount)
    text = texts.get_rub_prompt_text(action, crypto, rate)
    keyboard = keyboards.get_rub_input_keyboard(action, crypto)
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback_query.answer()

# --- Блок обработки ввода суммы ---

@router.message(TransactionStates.waiting_for_crypto_amount)
@router.message(TransactionStates.waiting_for_rub_amount)
async def process_amount_input(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.delete()
        data = await state.get_data()
        if last_id := data.get("last_bot_message_id"):
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_id,
                text="❌ Неверный формат. Введите положительное число (например: 0.001 или 1000):"
            )
        return

    await message.delete()  # убираем ввод пользователя

    data = await state.get_data()
    action, crypto = data["action"], data["crypto"]
    current_state = await state.get_state()
    rate = await crypto_rates.get_rate(crypto)
    if not rate:
        if last_id := data.get("last_bot_message_id"):
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_id,
                text=f"❌ Не удалось получить курс {crypto}. Попробуйте позже."
            )
        return

    # расчёт
    amount_rub, amount_crypto = (
        (amount, amount / rate)
        if current_state == TransactionStates.waiting_for_rub_amount
        else (amount * rate, amount)
    )

    # проверка промо
    promo_applied = False
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                if await get_user_activated_promo(cursor, message.from_user.id):
                    promo_applied = True
    except Exception as e:
        logger.error(f"DB error while checking promo: {e}", exc_info=True)

    service_commission_rub = 0.0 if promo_applied else amount_rub * (SERVICE_COMMISSION_PERCENT / 100)
    network_fee_rub = 0.0 if promo_applied else NETWORK_FEE_RUB
    total_amount = (amount_rub - service_commission_rub - network_fee_rub) if action == "sell" else (amount_rub + service_commission_rub + network_fee_rub)
    if total_amount < 0:
        total_amount = 0

    await state.update_data(
        amount_crypto=amount_crypto,
        amount_rub=amount_rub,
        total_amount=total_amount,
        service_commission_rub=service_commission_rub,
        network_fee_rub=network_fee_rub,
        promo_applied=promo_applied
    )

    prompt_text = texts.get_user_requisites_prompt_text(action, crypto)

    if last_id := data.get("last_bot_message_id"):
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=last_id,
            reply_markup=keyboards.get_cancel_keyboard(),
            text=prompt_text,
            parse_mode="HTML"
        )

    await state.set_state(TransactionStates.waiting_for_user_requisites)


@router.message(TransactionStates.waiting_for_user_requisites)
async def process_user_requisites_handler(message: Message, state: FSMContext, bot: Bot):
    user_requisites = message.text
    await message.delete()

    await state.update_data(user_requisites=user_requisites)
    data = await state.get_data()

    summary_text = texts.get_transaction_summary_text(
        action=data["action"],
        crypto=data["crypto"],
        amount_crypto=data["amount_crypto"],
        amount_rub=data["amount_rub"],
        total_amount=data["total_amount"],
        service_commission_rub=data["service_commission_rub"],
        network_fee_rub=data["network_fee_rub"],
        promo_applied=data["promo_applied"],
        user_requisites=data["user_requisites"]
    )

    if last_id := data.get("last_bot_message_id"):
        msg = await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=last_id,
            text=summary_text,
            reply_markup=keyboards.get_final_confirmation_keyboard(),
            parse_mode="HTML"
        )
        # обновляем id, чтобы потом финал тоже редактировался
        await state.update_data(last_bot_message_id=msg.message_id)

    await state.set_state(None)  # ждем подтверждения кнопкой

@router.callback_query(F.data == 'final_confirm_and_get_requisites')
async def final_confirm_handler(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    """
    (ШАГ 3) Ловит нажатие финальной кнопки, СОЗДАЕТ ЗАЯВКУ и переводит в чат.
    """
    user_id = callback_query.from_user.id
    if await get_active_order_for_user(user_id):
        await callback_query.message.edit_text("❗️ <b>У вас уже есть активная заявка.</b>")
        await callback_query.answer()
        return
        
    
    data = await state.get_data()
    user_requisites = data.get('user_requisites', 'Не указаны')
    
    try:
        await _create_order_and_enter_chat(bot, state, user_id, callback_query.from_user, user_requisites, message_to_edit=callback_query.message)
    except Exception as e:
        logger.error(f"CRITICAL ERROR in final_confirm_handler for user {user_id}: {e}", exc_info=True)
        await callback_query.message.answer("❌ Произошла критическая ошибка при создании заявки. Сообщите оператору.")
    finally:
        await callback_query.answer()


async def _create_order_and_enter_chat(bot: Bot, state: FSMContext, user_id: int, from_user, user_requisites: str,  message_to_edit: Message):
    """
    Вспомогательная функция: создает заявку, уведомляет всех и переводит пользователя в режим чата.
    """
    # ... (эта функция остается без изменений) ...
    data = await state.get_data()
    user_id = from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.cursor() as cursor:
            settings = await get_all_settings(cursor)
            topic = await bot.create_forum_topic(
                chat_id=SUPPORT_GROUP_ID, name=f"Заявка от {from_user.full_name}"
            )
            promo_code = await get_user_activated_promo(cursor, user_id) if data.get('promo_applied') else None
            order_id = await create_order(
                cursor, user_id=user_id, topic_id=topic.message_thread_id,
                username=from_user.username or "Нет username", action=data.get('action'),
                crypto=data.get('crypto'), amount_crypto=data.get('amount_crypto'),
                amount_rub=data.get('total_amount'), phone_and_bank=user_requisites, promo_code=promo_code
            )
            if promo_code:
                await clear_user_activated_promo(cursor, user_id)
            await db.commit()

    order_number = order_id + 9999
    await bot.edit_forum_topic(
        chat_id=SUPPORT_GROUP_ID, message_thread_id=topic.message_thread_id,
        name=f"Заявка #{order_number} от {from_user.full_name}"
    )
    admin_text, admin_keyboard = texts.get_admin_order_notification_for_topic(
        order_id=order_id, order_number=order_number, user_id=user_id,
        username=from_user.username or from_user.full_name,
        order_data=data, user_input=user_requisites
    )
    await bot.send_message(
        chat_id=SUPPORT_GROUP_ID, message_thread_id=topic.message_thread_id,
        text=admin_text, reply_markup=admin_keyboard, parse_mode="HTML"
    )
    
    action = data.get('action')
    crypto = data.get('crypto')
    total_amount = data.get('total_amount')
    sbp_phone = settings.get('sbp_phone', 'Не задан')
    sbp_bank = settings.get('sbp_bank', 'Не задан')
    wallet_address = settings.get(f'wallet_{crypto.lower()}', "Адрес не найден")
    
    final_text = texts.get_requisites_and_chat_prompt_text(
        action, crypto, total_amount, sbp_phone, sbp_bank, wallet_address
    )
    
    
    
    await message_to_edit.edit_text(
        final_text,
        reply_markup=keyboards.get_final_actions_keyboard(order_id), 
        parse_mode="HTML"
    )

    await state.set_state(TransactionStates.waiting_for_operator_reply)


# --- Блок выбора способа оплаты и создания заявки ---

@router.callback_query(F.data == 'get_requisites')
async def get_requisites_handler(callback_query: CallbackQuery, state: FSMContext):
    """
    (ИЗМЕНЕНО) Универсальный обработчик кнопки 'Получить реквизиты'.
    Теперь ВСЕГДА запрашивает реквизиты у пользователя, просто с разным текстом.
    """
    user_id = callback_query.from_user.id
    data = await state.get_data()
    action = data.get('action')
    crypto = data.get('crypto') # Нам нужна крипта для текста

    await callback_query.message.edit_reply_markup(None)
    await callback_query.answer()

    if await get_active_order_for_user(user_id):
        await callback_query.message.answer(
            "❗️ <b>У вас уже есть активная заявка.</b>\nЗавершите или отмените её, прежде чем создавать новую.", parse_mode="HTML"
        )
        return

    # Получаем правильный текст-приглашение (для buy - кошелек, для sell - банк)
    prompt_text = texts.get_user_requisites_prompt_text(action, crypto)
    
    await callback_query.message.answer(prompt_text, parse_mode="HTML")
    await state.set_state(TransactionStates.waiting_for_user_requisites)

        
# --- Блок отмены ---

@router.callback_query(F.data == 'cancel_transaction')
async def cancel_transaction_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик полной отмены FSM-операции."""
    await state.clear()
    await callback_query.message.delete()
    await callback_query.answer("Действие отменено.")
    from handlers.main import start_command_handler
    await start_command_handler(callback_query)

@router.callback_query(F.data.startswith('cancel_order_'))
async def cancel_order_handler(callback_query: CallbackQuery):
    """
    (ИЗМЕНЕНО) Обработчик отмены заявки с уведомлением в группе.
    """
    try:
        order_id = int(callback_query.data.split('_')[2])
    except (IndexError, ValueError):
        await callback_query.answer("Ошибка в данных кнопки!", show_alert=True)
        return

    order_info = None  # Инициализируем переменную для доступа вне блока try
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # 1. Сначала получаем информацию о заявке
                order_info = await get_order_by_id(cursor, order_id)

                if not order_info:
                    await callback_query.answer("Заявка не найдена!", show_alert=True)
                    return
                
                if order_info['status'] == 'completed':
                    await callback_query.answer("Заявка уже выполнена, отменить нельзя.", show_alert=True)
                    return
                
                # 2. Обновляем статус в БД
                await update_order_status(cursor, order_id, "cancelled_by_user")
                await refund_promo_if_needed(cursor, callback_query.from_user.id, order_id)
                await db.commit()
    except Exception as e:
        logger.error(f"DB error in user cancel_order for order #{order_id}: {e}", exc_info=True)
        await callback_query.answer("Ошибка при отмене заявки в базе данных!", show_alert=True)
        return

    # 3. Отправляем уведомление в тему, если отмена в БД прошла успешно
    if order_info and order_info.get('topic_id'):
        try:
            await callback_query.bot.send_message(
                chat_id=SUPPORT_GROUP_ID,
                message_thread_id=order_info['topic_id'],
                text="❌ <b>Пользователь отменил заявку.</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            # Если не удалось отправить (например, тема удалена), просто логируем
            logger.warning(f"Could not send cancellation notice to topic for order #{order_id}: {e}")

    # 4. Отвечаем пользователю
    await callback_query.message.delete()
    await callback_query.answer("✅ Заявка отменена.")
    
    # Возвращаем пользователя в главное меню
    from handlers.main import start_command_handler
    await start_command_handler(callback_query)
    
