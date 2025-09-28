# handlers/crypto.py (ФИНАЛЬНАЯ ВЕРСИЯ, РЕШАЮЩАЯ ПРОБЛЕМУ С NameError)

import aiosqlite
from aiogram.types import CallbackQuery, Message, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import AiogramError

from config import SUPPORT_GROUP_ID, SERVICE_COMMISSION_PERCENT, NETWORK_FEE_RUB, CRYPTO_WALLETS, SBP_PHONE, SBP_BANK
from utils.logging_config import logger
from utils.states import TransactionStates
from utils.callbacks import CryptoSelection, RubInputSwitch, CryptoInputSwitch
from utils.crypto_rates import crypto_rates
import utils.texts as texts
from handlers.router import crypto_router as router
from aiogram import F

# Импортируем из новых файлов базы данных
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import (
    get_order_status, get_user_activated_promo, create_order, clear_user_activated_promo,
    update_order_status, refund_promo_if_needed
)
from utils.database.db_helpers import get_active_order_for_user

# --- Блок навигации и выбора ---

@router.callback_query(F.data == 'sell')
async def sell_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора продажи криптовалюты."""
    await state.clear()
    keyboard = texts.get_crypto_selection_keyboard("sell")
    try:
        await callback_query.message.edit_text(texts.SELL_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="Markdown")
    except AiogramError:
        await callback_query.message.answer(texts.SELL_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.message.delete()
    await callback_query.answer()

@router.callback_query(F.data == 'buy')
async def buy_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора покупки криптовалюты."""
    await state.clear()
    keyboard = texts.get_crypto_selection_keyboard("buy")
    try:
        await callback_query.message.edit_text(texts.BUY_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="Markdown")
    except AiogramError:
        await callback_query.message.answer(texts.BUY_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.message.delete()
    await callback_query.answer()

@router.callback_query(CryptoSelection.filter())
async def select_crypto_handler(callback_query: CallbackQuery, callback_data: CryptoSelection, state: FSMContext):
    """Универсальный обработчик выбора криптовалюты."""
    action = callback_data.action
    crypto = callback_data.crypto
    rate = await crypto_rates.get_rate(crypto)
    if not rate:
        await callback_query.answer(f"Не удалось получить курс {crypto}, попробуйте позже.", show_alert=True)
        return
    await state.update_data(action=action, crypto=crypto)
    await state.set_state(TransactionStates.waiting_for_crypto_amount)
    text = texts.get_crypto_prompt_text(action, crypto, rate)
    keyboard = texts.get_crypto_details_keyboard(action, crypto)
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
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
    keyboard = texts.get_rub_input_keyboard(action, crypto)
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()

# --- Блок обработки транзакции ---

@router.message(TransactionStates.waiting_for_crypto_amount)
@router.message(TransactionStates.waiting_for_rub_amount)
async def process_amount_input(message: Message, state: FSMContext):
    """Универсальный обработчик ввода суммы."""
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        await message.answer("❌ Неверный формат. Введите положительное число (например: 0.001 или 1000):")
        return
    data = await state.get_data()
    action, crypto, current_state = data.get('action'), data.get('crypto'), await state.get_state()
    rate = await crypto_rates.get_rate(crypto)
    if not rate:
        await message.answer(f"❌ Не удалось получить курс {crypto}. Попробуйте позже.")
        return
    if current_state == TransactionStates.waiting_for_rub_amount:
        amount_rub, amount_crypto = amount, amount / rate
    else:
        amount_crypto, amount_rub = amount, amount * rate
    promo_applied = False
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                if await get_user_activated_promo(cursor, message.from_user.id):
                    promo_applied = True
    except Exception as e:
        logger.error(f"DB error while checking promo: {e}", exc_info=True)
    if promo_applied:
        service_commission_rub, network_fee_rub = 0.0, 0.0
    else:
        service_commission_rub = amount_rub * (SERVICE_COMMISSION_PERCENT / 100)
        network_fee_rub = NETWORK_FEE_RUB
    total_amount = amount_rub - service_commission_rub - network_fee_rub if action == 'sell' else amount_rub + service_commission_rub + network_fee_rub
    if total_amount < 0: total_amount = 0
    await state.update_data(
        amount_crypto=amount_crypto, amount_rub=amount_rub, total_amount=total_amount,
        service_commission_rub=service_commission_rub, network_fee_rub=network_fee_rub,
        promo_applied=promo_applied
    )
    summary_text = texts.get_transaction_summary_text(
        action=action, crypto=crypto, amount_crypto=amount_crypto, amount_rub=amount_rub,
        total_amount=total_amount, service_commission_rub=service_commission_rub,
        network_fee_rub=network_fee_rub, promo_applied=promo_applied
    )
    await message.answer(summary_text, reply_markup=texts.get_payment_method_keyboard(), parse_mode="Markdown")
    await state.set_state(TransactionStates.waiting_for_payment_method)


@router.message(TransactionStates.waiting_for_phone)
async def phone_input_handler(message: Message, state: FSMContext):
    """
    Обрабатывает ввод реквизитов, создает тикет или показывает существующий.
    """
    user_id = message.from_user.id
    user_input = message.text.strip()
    data = await state.get_data()
    logger.info(f"User {user_id}: Starting phone_input_handler.")
    
    ### --- КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: ИНИЦИАЛИЗАЦИЯ ПЕРЕМЕННЫХ --- ###
    order_id = None
    topic_id = None
    
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                logger.info(f"User {user_id}: Checking for an active order...")
                # use db_helpers.get_active_order_for_user which manages its own connection
                active_order = await get_active_order_for_user(user_id)
                
                if active_order:
                    logger.warning(f"User {user_id}: Active order found: {active_order}")
                    order_id = active_order['order_id']
                    topic_id = active_order.get('topic_id')
                    if topic_id:
                        order_number = order_id + 9999
                        # Topic links removed — only show notice and actions
                        notice_text = texts.get_active_order_notice_text(order_number)
                        details_text = texts.get_final_confirmation_text(
                            action=active_order['action'], crypto=active_order['crypto'],
                            amount_crypto=active_order['amount_crypto'], total_amount=active_order['total_amount'],
                            user_input=active_order['user_input'], order_number=order_number
                        )
                        await message.answer(notice_text, parse_mode="Markdown")
                        await message.answer(
                            details_text,
                            reply_markup=texts.get_final_actions_keyboard(order_id),
                            parse_mode="Markdown"
                        )
                    else:
                        await message.answer("⚠️ Найдена старая активная заявка без чата. Обратитесь к оператору.")
                    return

                logger.info(f"User {user_id}: No active order found. Creating new one.")
                topic = await message.bot.create_forum_topic(
                    chat_id=SUPPORT_GROUP_ID, name=f"Заявка от {message.from_user.full_name}"
                )
                topic_id = topic.message_thread_id
                logger.info(f"User {user_id}: Created topic with ID {topic_id}.")
                promo_to_save = await get_user_activated_promo(cursor, user_id) if data.get('promo_applied') else None
                order_id = await create_order(
                    cursor, user_id=user_id, topic_id=topic_id,
                    username=message.from_user.username or "Нет username",
                    action=data.get('action'), crypto=data.get('crypto'),
                    amount_crypto=data.get('amount_crypto'), amount_rub=data.get('total_amount'),
                    phone_and_bank=user_input, promo_code=promo_to_save
                )
                if promo_to_save:
                    await clear_user_activated_promo(cursor, user_id)
                await db.commit()
                logger.info(f"User {user_id}: DB transaction committed. New order_id is {order_id}.")

        order_number = order_id + 9999
        logger.info(f"User {user_id}: Editing topic {topic_id} with new name...")
        await message.bot.edit_forum_topic(
            chat_id=SUPPORT_GROUP_ID,
            message_thread_id=topic_id,
            name=f"Заявка #{order_number} от {message.from_user.full_name}"
        )
        logger.info(f"User {user_id}: Edited topic name.")
        admin_text, admin_keyboard = texts.get_admin_order_notification_for_topic( # <-- ИСПРАВЛЕНО
        order_id=order_id,
        order_number=order_number,
        user_id=user_id,
        username=message.from_user.username or message.from_user.full_name,
        order_data=data,
        user_input=user_input
        )
        logger.info(f"User {user_id}: Sending details to topic {topic_id}...")
        await message.bot.send_message(
            chat_id=SUPPORT_GROUP_ID, message_thread_id=topic_id,
            text=admin_text, reply_markup=admin_keyboard, parse_mode="Markdown"
        )
        logger.info(f"User {user_id}: Details sent successfully.")
        final_text = texts.get_final_confirmation_text_with_topic(order_number)
        await message.answer(final_text, reply_markup=texts.get_final_actions_keyboard(order_id), parse_mode="Markdown")
        logger.info(f"User {user_id}: Final confirmation sent.")

    except Exception as e:
        logger.error(f"CRITICAL ERROR in phone_input_handler for user {user_id}: {e}", exc_info=True)
        await message.answer("❌ Произошла критическая ошибка при создании заявки. Сообщите оператору.")
    finally:
        await state.clear()
        logger.info(f"User {user_id}: phone_input_handler finished, state cleared.")

# --- Блок завершения и отмены ---

@router.callback_query(F.data == 'cancel_transaction')
async def cancel_transaction_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик полной отмены FSM-операции."""
    await state.clear()
    await callback_query.answer("Действие отменено.")
    from handlers.main import start_handler
    await start_handler(callback_query)

@router.callback_query(F.data == 'cancel_order')
async def cancel_order_handler(callback_query: CallbackQuery):
    """Обработчик отмены уже созданной заявки пользователем."""
    parts = callback_query.data.split('_')
    if len(parts) != 3:
        await callback_query.answer("Ошибка в данных кнопки!", show_alert=True)
        return
    try:
        order_id = int(parts[2])
    except ValueError:
        await callback_query.answer("Не удалось извлечь ID из кнопки!", show_alert=True)
        return
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                if await get_order_status(cursor, order_id) == 'completed':
                    await callback_query.answer("Заявка уже подтверждена, отменить нельзя.", show_alert=True)
                    return
                await update_order_status(cursor, order_id, "cancelled_by_user")
                await refund_promo_if_needed(cursor, callback_query.from_user.id, order_id)
                await db.commit()
    except Exception as e:
        logger.error(f"DB error in user cancel_order for order #{order_id}: {e}", exc_info=True)
    try:
        await callback_query.message.delete()
    except AiogramError: pass
    from handlers.main import start_handler
    await start_handler(callback_query)
    await callback_query.answer("Заявка отменена")


@router.callback_query(F.data == 'reply_to_active_order')
@router.callback_query(F.data == 'reply_to_operator')
async def initiate_operator_reply(callback_query: CallbackQuery, state: FSMContext):
    """Унифицированный обработчик, инициирующий отправку сообщения пользователем в тему его заявки.
    Ставит состояние ожидания ответа оператору и показывает prompt.
    """
    # Delegate to proxy contract to handle checks and prompting
    # Use a safe loader: try to import the proxy module from the handlers package
    # (handlers.crypto.proxy) first; if that fails (module name ambiguity or
    # repository-local import issues), fall back to loading the proxy.py by file path.
    try:
        from handlers.crypto import proxy as proxy_mod
    except Exception:
        # Fallback: load proxy.py by absolute path to avoid ModuleNotFoundError
        import importlib.util
        import sys
        import pathlib

        repo_root = pathlib.Path(__file__).resolve().parents[1]
        proxy_path = repo_root / 'handlers' / 'crypto' / 'proxy.py'
        spec = importlib.util.spec_from_file_location('handlers.crypto.proxy', str(proxy_path))
        proxy_mod = importlib.util.module_from_spec(spec)
        sys.modules['handlers.crypto.proxy'] = proxy_mod
        spec.loader.exec_module(proxy_mod)

    res = await proxy_mod.start_user_reply_prompt(callback_query, state)
    if not res.ok:
        if res.code == 'db_error':
            await callback_query.answer("❌ Ошибка базы данных.", show_alert=True)
        elif res.code == 'no_active_order':
            await callback_query.answer("⚠️ У вас нет активных заявок для ответа.", show_alert=True)
    return


@router.message(TransactionStates.waiting_for_operator_reply)
async def operator_reply_handler(message: Message, state: FSMContext):
    """Унифицированный message-handler, пересылающий сообщение пользователя в тему его заявки."""
    # Use the same safe loader as above to import handlers.crypto.proxy
    try:
        from handlers.crypto import proxy as proxy_mod
    except Exception:
        import importlib.util
        import sys
        import pathlib

        repo_root = pathlib.Path(__file__).resolve().parents[1]
        proxy_path = repo_root / 'handlers' / 'crypto' / 'proxy.py'
        spec = importlib.util.spec_from_file_location('handlers.crypto.proxy', str(proxy_path))
        proxy_mod = importlib.util.module_from_spec(spec)
        sys.modules['handlers.crypto.proxy'] = proxy_mod
        spec.loader.exec_module(proxy_mod)

    await proxy_mod.handle_user_message_to_topic(message, state)


@router.callback_query(F.data == 'payment_sbp')
async def payment_sbp_handler(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора способа оплаты "СБП".
    Показывает пользователю реквизиты для перевода и запрашивает его реквизиты.
    """
    data = await state.get_data()
    
    # Безопасно извлекаем все необходимые данные из состояния
    action = data.get('action')
    crypto = data.get('crypto')
    amount_crypto = data.get('amount_crypto')
    amount_rub = data.get('amount_rub') # "Чистая" сумма
    total_amount = data.get('total_amount') # Итоговая сумма с комиссиями

    # Проверка на случай, если состояние было утеряно
    if not all([action, crypto, amount_crypto is not None, amount_rub is not None, total_amount is not None]):
        await callback_query.answer("❌ Ошибка: данные транзакции утеряны. Пожалуйста, начните заново.", show_alert=True)
        await state.clear()
        # Можно вернуть пользователя в главное меню
        from handlers.main import start_handler
        await start_handler(callback_query)
        return

    # Генерируем текст в зависимости от действия (покупка или продажа)
    if action == 'sell':
        # Пользователь продает крипту -> мы показываем ему НАШ кошелек для пополнения
        wallet_address = CRYPTO_WALLETS.get(crypto)
        text = texts.get_sbp_sell_details_text(crypto, amount_crypto, amount_rub, wallet_address)
    else: # buy
        # Пользователь покупает крипту -> мы показываем ему НАШИ реквизиты СБП
        text = texts.get_sbp_buy_details_text(crypto, amount_crypto, total_amount, SBP_PHONE, SBP_BANK)
    
    # Редактируем предыдущее сообщение, показывая новые инструкции
    await callback_query.message.edit_text(
        text, 
        parse_mode="Markdown", 
        # Добавляем кнопку "Отмена", чтобы пользователь мог выйти из процесса
        reply_markup=texts.get_cancel_keyboard() 
    )
    
    # Устанавливаем следующее состояние: ожидание реквизитов от пользователя
    await state.set_state(TransactionStates.waiting_for_phone)
    await callback_query.answer()
    # (Удалены старые дубликаты — оставлены унифицированные handlers выше)
