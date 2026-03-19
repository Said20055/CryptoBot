# handlers/trade.py
"""
FSM-флоу покупки и продажи криптовалюты.
"""

import asyncio

from aiogram import F, Bot, Router
from aiogram.exceptions import AiogramError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import (
    NETWORK_FEE_RUB, ORDER_GREETING_DELAY_SECONDS, ORDER_NUMBER_OFFSET,
    SERVICE_COMMISSION_PERCENT, SUPPORT_GROUP_ID,
)
from utils import keyboards, texts
from utils.callbacks import CancelOrder, CryptoSelection, RubInputSwitch
from utils.crypto_rates import crypto_rates
from utils.logging_config import logger
from utils.states import TransactionStates
from utils.texts import WELCOME_PHOTO_URL, WELCOME_TEXT
from utils.database.db_helpers import acquire, transaction
from utils.database.db_queries import (
    clear_user_activated_promo, create_order, get_active_order_for_user,
    get_all_settings, get_order_by_id, get_promo_discount_info,
    get_user_activated_promo, refund_promo_if_needed, update_order_status,
)

router = Router()


async def _send_delayed_greeting(bot: Bot, user_id: int):
    try:
        await asyncio.sleep(ORDER_GREETING_DELAY_SECONDS)
        await bot.send_message(
            chat_id=user_id,
            text="Приветствую, оператор будет на связи в течение 5 минут!",
        )
    except Exception as e:
        logger.warning(f"Could not send delayed greeting to user {user_id}: {e}")


async def _show_main_menu(msg: Message):
    try:
        await msg.answer_photo(
            photo=WELCOME_PHOTO_URL,
            caption=WELCOME_TEXT,
            reply_markup=keyboards.get_main_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        await msg.answer(WELCOME_TEXT, reply_markup=keyboards.get_main_keyboard(), parse_mode="HTML")


# --- Выбор действия ---

@router.callback_query(F.data == "sell")
async def sell_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    keyboard = keyboards.get_crypto_selection_keyboard("sell")
    try:
        await callback.message.edit_text(texts.SELL_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="HTML")
    except AiogramError:
        await callback.message.delete()
        await callback.message.answer(texts.SELL_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "buy")
async def buy_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    keyboard = keyboards.get_crypto_selection_keyboard("buy")
    try:
        await callback.message.edit_text(texts.BUY_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="HTML")
    except AiogramError:
        await callback.message.delete()
        await callback.message.answer(texts.BUY_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(CryptoSelection.filter())
async def select_crypto_handler(callback: CallbackQuery, callback_data: CryptoSelection, state: FSMContext):
    action, crypto = callback_data.action, callback_data.crypto
    rate = await crypto_rates.get_rate(crypto)
    if not rate:
        await callback.answer(f"Не удалось получить курс {crypto}, попробуйте позже.", show_alert=True)
        return

    await state.update_data(action=action, crypto=crypto)
    await state.set_state(TransactionStates.waiting_for_crypto_amount)

    text = texts.get_crypto_prompt_text(action, crypto, rate)
    msg = await callback.message.edit_text(text, reply_markup=keyboards.get_crypto_details_keyboard(action, crypto), parse_mode="HTML")
    await state.update_data(last_bot_message_id=msg.message_id)
    await callback.answer()


@router.callback_query(RubInputSwitch.filter())
async def switch_to_rub_handler(callback: CallbackQuery, callback_data: RubInputSwitch, state: FSMContext):
    action, crypto = callback_data.action, callback_data.crypto
    rate = await crypto_rates.get_rate(crypto)
    if not rate:
        await callback.answer(f"Не удалось получить курс {crypto}, попробуйте позже.", show_alert=True)
        return

    await state.set_state(TransactionStates.waiting_for_rub_amount)
    await callback.message.edit_text(
        texts.get_rub_prompt_text(action, crypto, rate),
        reply_markup=keyboards.get_rub_input_keyboard(action, crypto),
        parse_mode="HTML",
    )
    await callback.answer()


# --- Ввод суммы ---

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
                chat_id=message.chat.id, message_id=last_id,
                text="❌ Неверный формат. Введите положительное число (например: 0.001 или 1000):",
            )
        return

    await message.delete()
    data = await state.get_data()
    action, crypto = data["action"], data["crypto"]
    current_state = await state.get_state()

    rate = await crypto_rates.get_rate(crypto)
    if not rate:
        if last_id := data.get("last_bot_message_id"):
            await bot.edit_message_text(
                chat_id=message.chat.id, message_id=last_id,
                text=f"❌ Не удалось получить курс {crypto}. Попробуйте позже.",
            )
        return

    if current_state == TransactionStates.waiting_for_rub_amount:
        amount_rub, amount_crypto = amount, amount / rate
    else:
        amount_rub, amount_crypto = amount * rate, amount

    promo_code = None
    promo_discount_amount = 0.0
    promo_discount_type = 'percent'
    try:
        async with acquire() as conn:
            promo_code = await get_user_activated_promo(conn, message.from_user.id)
            if promo_code:
                promo_discount_amount, promo_discount_type = await get_promo_discount_info(conn, promo_code)
    except Exception as e:
        logger.error(f"DB error while checking promo: {e}", exc_info=True)

    base_service = amount_rub * (SERVICE_COMMISSION_PERCENT / 100)
    base_network = float(NETWORK_FEE_RUB)
    total_base = base_service + base_network

    if promo_code:
        if promo_discount_type == 'percent':
            promo_discount_rub = min(total_base * (promo_discount_amount / 100), total_base)
        else:
            promo_discount_rub = min(promo_discount_amount, total_base)
    else:
        promo_discount_rub = 0.0

    service_discount = min(base_service, promo_discount_rub)
    network_discount = min(base_network, promo_discount_rub - service_discount)
    service_commission_rub = base_service - service_discount
    network_fee_rub = base_network - network_discount
    promo_applied = promo_discount_rub > 0

    total_amount = max(
        0.0,
        (amount_rub - service_commission_rub - network_fee_rub) if action == "sell"
        else (amount_rub + service_commission_rub + network_fee_rub),
    )

    await state.update_data(
        amount_crypto=amount_crypto, amount_rub=amount_rub, total_amount=total_amount,
        service_commission_rub=service_commission_rub, network_fee_rub=network_fee_rub,
        base_service_rub=base_service, base_network_rub=base_network,
        promo_applied=promo_applied, promo_discount_rub=promo_discount_rub, promo_code=promo_code,
    )

    if last_id := data.get("last_bot_message_id"):
        await bot.edit_message_text(
            chat_id=message.chat.id, message_id=last_id,
            text=texts.get_user_requisites_prompt_text(action, crypto),
            reply_markup=keyboards.get_cancel_keyboard(),
            parse_mode="HTML",
        )
    await state.set_state(TransactionStates.waiting_for_user_requisites)


@router.message(TransactionStates.waiting_for_user_requisites)
async def process_user_requisites(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    user_requisites = message.text
    await state.update_data(user_requisites=user_requisites)
    data = await state.get_data()

    summary = texts.get_transaction_summary_text(
        action=data["action"], crypto=data["crypto"],
        amount_crypto=data["amount_crypto"], amount_rub=data["amount_rub"],
        total_amount=data["total_amount"],
        base_service_rub=data.get("base_service_rub", data["service_commission_rub"]),
        base_network_rub=data.get("base_network_rub", data["network_fee_rub"]),
        promo_applied=data["promo_applied"],
        promo_discount_rub=data.get("promo_discount_rub", 0.0),
        user_requisites=user_requisites,
    )

    if last_id := data.get("last_bot_message_id"):
        msg = await bot.edit_message_text(
            chat_id=message.chat.id, message_id=last_id,
            text=summary,
            reply_markup=keyboards.get_final_confirmation_keyboard(),
            parse_mode="HTML",
        )
        await state.update_data(last_bot_message_id=msg.message_id)
    await state.set_state(None)


# --- Подтверждение и создание заявки ---

@router.callback_query(F.data == "final_confirm_and_get_requisites")
async def final_confirm_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id

    try:
        async with acquire() as conn:
            active = await get_active_order_for_user(conn, user_id)
    except Exception as e:
        logger.error(f"DB error checking active order for user {user_id}: {e}", exc_info=True)
        await callback.answer("Ошибка базы данных.", show_alert=True)
        return

    if active:
        await callback.message.edit_text("❗️ <b>У вас уже есть активная заявка.</b>", parse_mode="HTML")
        await callback.answer()
        return

    data = await state.get_data()
    try:
        await _create_order_and_enter_chat(
            bot=bot, state=state, from_user=callback.from_user,
            user_requisites=data.get('user_requisites', 'Не указаны'),
            message_to_edit=callback.message,
        )
    except Exception as e:
        logger.error(f"CRITICAL ERROR in final_confirm_handler for user {user_id}: {e}", exc_info=True)
        await callback.message.answer("❌ Произошла критическая ошибка при создании заявки. Сообщите оператору.")
    finally:
        await callback.answer()


async def _create_order_and_enter_chat(bot: Bot, state: FSMContext, from_user,
                                        user_requisites: str, message_to_edit: Message):
    data = await state.get_data()
    user_id = from_user.id

    async with transaction() as conn:
        settings = await get_all_settings(conn)
        topic = await bot.create_forum_topic(
            chat_id=SUPPORT_GROUP_ID, name=f"Заявка от {from_user.full_name}"
        )
        promo_code = data.get('promo_code')
        order_id = await create_order(
            conn, user_id=user_id, topic_id=topic.message_thread_id,
            username=from_user.username or "Нет username",
            action=data.get('action'), crypto=data.get('crypto'),
            amount_crypto=data.get('amount_crypto'),
            amount_rub=data.get('total_amount'),
            phone_and_bank=user_requisites, promo_code=promo_code,
            service_commission_rub=data.get('service_commission_rub', 0.0),
            network_fee_rub=data.get('network_fee_rub', 0.0),
        )
        if promo_code:
            await clear_user_activated_promo(conn, user_id)

    order_number = order_id + ORDER_NUMBER_OFFSET
    await bot.edit_forum_topic(
        chat_id=SUPPORT_GROUP_ID, message_thread_id=topic.message_thread_id,
        name=f"Заявка #{order_number} от {from_user.full_name}",
    )

    admin_text = texts.get_admin_order_notification_text(
        order_id=order_id, order_number=order_number, user_id=user_id,
        username=from_user.username or from_user.full_name,
        order_data=data, user_input=user_requisites,
    )
    admin_keyboard = keyboards.get_admin_order_keyboard(order_id, user_id)
    await bot.send_message(
        chat_id=SUPPORT_GROUP_ID, message_thread_id=topic.message_thread_id,
        text=admin_text, reply_markup=admin_keyboard, parse_mode="HTML",
    )

    crypto = data.get('crypto')
    sbp_phone = settings.get('sbp_phone', 'Не задан')
    sbp_bank = settings.get('sbp_bank', 'Не задан')
    wallet_address = settings.get(f'wallet_{crypto.lower()}', "Адрес не найден")

    await message_to_edit.edit_text(
        texts.get_requisites_and_chat_prompt_text(
            data.get('action'), crypto, data.get('total_amount'),
            sbp_phone, sbp_bank, wallet_address,
        ),
        reply_markup=keyboards.get_final_actions_keyboard(order_id),
        parse_mode="HTML",
    )
    asyncio.create_task(_send_delayed_greeting(bot, user_id))
    await state.set_state(TransactionStates.waiting_for_operator_reply)


# --- Загрузка чека ---

@router.callback_query(F.data == "upload_receipt")
async def upload_receipt_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TransactionStates.waiting_for_operator_reply)
    await callback.message.answer("📎 Пожалуйста, отправьте чек одним сообщением (фото или файл).")
    await callback.answer()


# --- Отмена ---

@router.callback_query(F.data == "cancel_transaction")
async def cancel_transaction_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except AiogramError:
        pass
    await callback.answer("Действие отменено.")
    await _show_main_menu(callback.message)


@router.callback_query(CancelOrder.filter())
async def cancel_order_handler(callback: CallbackQuery, callback_data: CancelOrder):
    order_id = callback_data.order_id

    try:
        async with transaction() as conn:
            order_info = await get_order_by_id(conn, order_id)
            if not order_info:
                await callback.answer("Заявка не найдена!", show_alert=True)
                return
            if order_info['status'] == 'completed':
                await callback.answer("Заявка уже выполнена, отменить нельзя.", show_alert=True)
                return
            if order_info['status'] in ('rejected', 'auto_closed', 'cancelled_by_user'):
                await callback.answer("Заявка уже закрыта.", show_alert=True)
                return
            await update_order_status(conn, order_id, "cancelled_by_user")
            await refund_promo_if_needed(conn, callback.from_user.id, order_id)
    except Exception as e:
        logger.error(f"DB error in cancel_order for order #{order_id}: {e}", exc_info=True)
        await callback.answer("Ошибка при отмене заявки в базе данных!", show_alert=True)
        return

    if order_info and order_info.get('topic_id'):
        try:
            await callback.bot.send_message(
                chat_id=SUPPORT_GROUP_ID,
                message_thread_id=order_info['topic_id'],
                text="❌ <b>Пользователь отменил заявку.</b>",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Could not send cancellation notice to topic for order #{order_id}: {e}")

    await callback.answer("✅ Заявка отменена.")
    try:
        await callback.message.delete()
    except AiogramError:
        pass
    await _show_main_menu(callback.message)
