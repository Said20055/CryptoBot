from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import AiogramError
import aiosqlite
from config import ADMIN_CHAT_ID, CRYPTO_WALLETS, NETWORK_FEE_RUB, SBP_BANK, SBP_PHONE, SERVICE_COMMISSION_PERCENT
from utils.logging_config import logger
from utils.states import TransactionStates
from utils.callbacks import CryptoSelection, RubInputSwitch # Импортируем фабрики
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import (
    get_user_activated_promo, create_order, clear_user_activated_promo, refund_promo_if_needed, update_order_status
)
from utils.crypto_rates import crypto_rates
import utils.texts as texts

# --- ОСНОВНЫЕ ХЕНДЛЕРЫ МЕНЮ (SELL/BUY) ---

async def sell_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора продажи криптовалюты."""
    await state.clear()
    keyboard = texts.get_crypto_selection_keyboard("sell")
    await callback_query.message.answer(texts.SELL_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="Markdown")
    try:
        await callback_query.message.delete()
    except AiogramError as e:
        logger.warning(f"Could not delete message: {e}")
    await callback_query.answer()

async def buy_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора покупки криптовалюты."""
    await state.clear()
    keyboard = texts.get_crypto_selection_keyboard("buy")
    await callback_query.message.answer(texts.BUY_CRYPTO_TEXT, reply_markup=keyboard, parse_mode="Markdown")
    try:
        await callback_query.message.delete()
    except AiogramError as e:
        logger.warning(f"Could not delete message: {e}")
    await callback_query.answer()

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
    action = data.get('action')
    crypto = data.get('crypto')
    current_state = await state.get_state()

    rate = await crypto_rates.get_rate(crypto)
    if not rate:
        await message.answer(f"❌ Не удалось получить курс {crypto}. Попробуйте позже.")
        return

    if current_state == TransactionStates.waiting_for_rub_amount:
        amount_rub = amount
        amount_crypto = amount / rate
    else:
        amount_crypto = amount
        amount_rub = amount * rate

    # --- ИЗМЕНЕНИЕ: Логика промокодов с новым паттерном ---
    promo_applied = False
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                activated_promo = await get_user_activated_promo(cursor, message.from_user.id)
                if activated_promo:
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

async def payment_sbp_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора СБП."""
    data = await state.get_data()
    action = data.get('action')
    crypto = data.get('crypto')
    amount_crypto = data.get('amount_crypto')
    amount_rub = data.get('amount_rub')
    total_amount = data.get('total_amount')

    if not all([action, crypto, amount_crypto is not None, amount_rub is not None]):
        await callback_query.answer("❌ Ошибка: данные транзакции утеряны. Начните заново.", show_alert=True)
        await state.clear()
        return

    if action == 'sell':
        # Пользователь продает крипту, значит он ПОЛУЧИТ 'чистую' сумму
        wallet_address = CRYPTO_WALLETS.get(crypto)
        text = texts.get_sbp_sell_details_text(crypto, amount_crypto, amount_rub, wallet_address)
    else: # buy
        # Пользователь покупает крипту, значит он ЗАПЛАТИТ итоговую сумму с комиссиями
        text = texts.get_sbp_buy_details_text(crypto, amount_crypto, total_amount, SBP_PHONE, SBP_BANK)
    
    await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=texts.get_back_to_main_menu_keyboard())
    await state.set_state(TransactionStates.waiting_for_phone)
    await callback_query.answer()

async def payment_operator_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора оператора для оплаты."""
    data = await state.get_data()
    action = data.get('action')

    if action: # Если есть активная транзакция
        user_id = callback_query.from_user.id
        username = callback_query.from_user.username or callback_query.from_user.full_name

        # Формируем текст для пользователя и админов
        user_text, admin_text = texts.get_operator_request_texts(username, user_id, data)
        admin_keyboard = texts.get_admin_reply_keyboard(user_id)

        # Безопасно уведомляем админов
        for admin_id in ADMIN_CHAT_ID:
            try:
                await callback_query.bot.send_message(
                    admin_id, admin_text, reply_markup=admin_keyboard, parse_mode="Markdown"
                )
                logger.info(f"Operator request from user {user_id} sent to admin {admin_id}")
            except AiogramError as e:
                logger.error(f"Failed to send operator request to admin {admin_id}: {e}")
        
        await callback_query.message.edit_text(user_text, parse_mode="Markdown", reply_markup=texts.get_back_to_main_menu_keyboard())
        await state.set_state(TransactionStates.waiting_for_phone)
    else: # Если транзакции нет, просто показываем контакт
        await callback_query.message.answer(texts.OPERATOR_CONTACT_TEXT)
    
    await callback_query.answer()

async def phone_input_handler(message: Message, state: FSMContext):
    """Обработчик ввода реквизитов, создания заявки и управления промокодом."""
    user_input = message.text.strip()
    data = await state.get_data()
    
    order_id = 0 # Инициализируем
    # --- ИЗМЕНЕНИЕ: Новый паттерн работы с БД ---
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                promo_to_save = None
                if data.get('promo_applied'):
                    promo_to_save = await get_user_activated_promo(cursor, message.from_user.id)
                
                order_id = await create_order(
                    cursor, user_id=message.from_user.id,
                    username=message.from_user.username or message.from_user.full_name,
                    action=data.get('action'), crypto=data.get('crypto'),
                    amount_crypto=data.get('amount_crypto'), amount_rub=data.get('total_amount'),
                    phone_and_bank=user_input, promo_code=promo_to_save
                )
                
                if promo_to_save:
                    await clear_user_activated_promo(cursor, message.from_user.id)

                await db.commit()
                
    except Exception as e:
        logger.error(f"Database error in phone_input_handler: {e}", exc_info=True)
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.")
        await state.clear()
        return

    order_number = order_id + 9999
    
    final_text = texts.get_final_confirmation_text(
        data.get('action'), data.get('crypto'), data.get('amount_crypto'), 
        data.get('total_amount'), user_input, order_number
    )
    await message.answer(final_text, reply_markup=texts.get_final_actions_keyboard(order_id=order_id), parse_mode="Markdown")
    
    admin_text, admin_keyboard = texts.get_admin_order_notification(
        order_id=order_id, order_number=order_number, user_id=message.from_user.id,
        username=message.from_user.username or message.from_user.full_name,
        order_data=data, user_input=user_input
    )
    
    for admin_id in ADMIN_CHAT_ID:
        try:
            await message.bot.send_message(
                admin_id, admin_text, reply_markup=admin_keyboard, parse_mode="Markdown"
            )
            logger.info(f"Order #{order_number} notification sent to admin {admin_id}")
        except AiogramError as e:
            logger.error(f"Failed to notify admin {admin_id} about order #{order_number}: {e}")
    
    await state.clear()
async def cancel_transaction_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик полной отмены FSM-операции."""
    await state.clear()
    await callback_query.answer("Действие отменено.")
    from handlers.main import start_handler
    await start_handler(callback_query)

async def cancel_order_handler(callback_query: CallbackQuery):
    """
    Обработчик отмены уже созданной заявки пользователем (ФИНАЛЬНАЯ ВЕРСИЯ).
    Возвращает промокод, если он был использован.
    """
    parts = callback_query.data.split('_')
    
    # Парсим ID заявки из callback_data ('cancel_order_123')
    if len(parts) != 3:
        logger.error(f"Invalid callback data format for user cancel_order: {callback_query.data}")
        await callback_query.answer("Ошибка в данных кнопки!", show_alert=True)
        return

    try:
        order_id = int(parts[2])
    except ValueError:
        logger.error(f"Could not parse order_id from callback: {callback_query.data}")
        await callback_query.answer("Не удалось извлечь ID из данных кнопки!", show_alert=True)
        return

    # --- НОВЫЙ ПАТТЕРН РАБОТЫ С БД ---
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # Вызываем ту же функцию, что и при отмене админом
                await update_order_status(cursor, order_id, "cancelled_by_user")
                await refund_promo_if_needed(cursor, callback_query.from_user.id, order_id)
                await db.commit()
    except Exception as e:
        logger.error(f"DB error in user cancel_order_handler for order #{order_id}: {e}", exc_info=True)
        # Сообщаем пользователю об ошибке, но продолжаем отмену
        await callback_query.answer("Ошибка базы данных при возврате промокода!", show_alert=True)
    # --- КОНЕЦ НОВОГО ПАТТЕРНА ---

    # Удаляем сообщение с кнопками
    try:
        await callback_query.message.delete()
    except AiogramError as e:
        logger.warning(f"Could not delete message: {e}")
    
    # Показываем главное меню
    from handlers.main import start_handler
    await start_handler(callback_query)
    await callback_query.answer("Заявка отменена")

async def send_tx_link_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик запроса ссылки на транзакцию."""
    await state.set_state(TransactionStates.waiting_for_tx_link)
    await callback_query.message.answer(texts.SEND_TX_LINK_PROMPT)
    await callback_query.answer()

async def tx_link_input_handler(message: Message, state: FSMContext):
    """Обработчик ввода ссылки на транзакцию."""
    tx_link = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name

    await message.reply("✅ Ссылка на транзакцию получена. Оператор скоро её проверит.")
    
    admin_text, admin_keyboard = texts.get_tx_link_notification(username, user_id, tx_link)
    
    for admin_id in ADMIN_CHAT_ID:
        try:
            await message.bot.send_message(
                admin_id, admin_text, reply_markup=admin_keyboard, parse_mode="Markdown"
            )
            logger.info(f"Transaction link from user {user_id} sent to admin {admin_id}")
        except AiogramError as e:
            logger.error(f"Failed to send tx link to admin {admin_id}: {e}")
    
    await state.clear()

async def reply_to_operator_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик запроса на отправку сообщения оператору."""
    await callback_query.message.answer(texts.REPLY_TO_OPERATOR_PROMPT)
    await state.set_state(TransactionStates.waiting_for_operator_reply)
    await callback_query.answer()

async def operator_reply_input_handler(message: Message, state: FSMContext):
    """Обработчик ввода сообщения для оператора."""
    user_reply = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    
    await message.reply("✅ Ваше сообщение отправлено оператору.")
    
    admin_text, admin_keyboard = texts.get_user_reply_notification(username, user_id, user_reply)
    
    for admin_id in ADMIN_CHAT_ID:
        try:
            await message.bot.send_message(
                admin_id, admin_text, reply_markup=admin_keyboard, parse_mode="Markdown"
            )
            logger.info(f"User reply from {user_id} sent to admin {admin_id}")
        except AiogramError as e:
            logger.error(f"Failed to send user reply to admin {admin_id}: {e}")
    
    await state.clear()