"""
Хендлеры для работы с криптовалютами.

Этот модуль содержит обработчики для создания заявок на обмен криптовалют,
ввода сумм, выбора способов оплаты и взаимодействия с пользователями.
"""

from utils.crypto_rates import crypto_rates
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import AiogramError
from utils.logging_config import logger
from utils.states import TransactionStates
import utils.texts as texts

async def sell_handler(callback_query: CallbackQuery):
    """Обработчик выбора продажи криптовалюты.
    
    Args:
        callback_query: Callback query от нажатия кнопки "Продать крипту"
    """
    keyboard = texts.get_crypto_selection_keyboard("sell")
    await callback_query.message.answer(texts.SELL_CRYPTO_TEXT, reply_markup=keyboard)
    try:
        await callback_query.message.delete()
    except (ConnectionError, TimeoutError) as e:
        logger.warning(f"Could not delete message: {e}")
    await callback_query.answer()

async def buy_handler(callback_query: CallbackQuery):
    """Обработчик выбора покупки криптовалюты.
    
    Args:
        callback_query: Callback query от нажатия кнопки "Купить крипту"
    """
    keyboard = texts.get_crypto_selection_keyboard("buy")
    await callback_query.message.answer(texts.BUY_CRYPTO_TEXT, reply_markup=keyboard)
    try:
        await callback_query.message.delete()
    except (ConnectionError, TimeoutError) as e:
        logger.warning(f"Could not delete message: {e}")
    await callback_query.answer()

async def _get_crypto_rate_and_fees(crypto: str, amount_rub: float = None):
    """Получить курс и комиссии для криптовалюты.
    
    Args:
        crypto: Код криптовалюты (BTC, LTC, TRX, USDT)
        amount_rub: Сумма в рублях для расчета комиссии сервиса
        
    Returns:
        tuple: (rate, network_fee_crypto, network_fee_rub, service_commission_rub) или (None, None, None, None) при ошибке
    """
    
    from config import NETWORK_FEE_RUB, SERVICE_COMMISSION_PERCENT
    
    rate = await crypto_rates.get_rate(crypto)
    if not rate:
        return None, None, None, None
    
    network_fee_crypto = crypto_rates.network_fees[crypto]
    
    # Фиксированная комиссия сети
    network_fee_rub = NETWORK_FEE_RUB
    
    # Комиссия сервиса (процент от суммы)
    if amount_rub is not None:
        service_commission_rub = amount_rub * (SERVICE_COMMISSION_PERCENT / 100)
    else:
        service_commission_rub = 0
    
    return rate, network_fee_crypto, network_fee_rub, service_commission_rub

async def _handle_crypto_selection(callback_query: CallbackQuery, state: FSMContext, action: str, crypto: str):
    """Общий обработчик выбора криптовалюты.
    
    Args:
        callback_query: Callback query от нажатия кнопки криптовалюты
        state: FSM состояние
        action: Действие ("sell" или "buy")
        crypto: Код криптовалюты
    """
    rate, network_fee_crypto, network_fee_rub, _ = await _get_crypto_rate_and_fees(crypto)
    
    if not rate:
        await callback_query.message.answer(
            f"Ошибка получения курса {crypto}. Попробуйте позже.")
        await callback_query.answer()
        return
    
    # Сохраняем данные в состоянии; по умолчанию ждём ввод в криптовалюте
    await state.update_data(action=action, crypto=crypto, input_mode="crypto")
    await state.set_state(TransactionStates.waiting_for_crypto_amount)
    
    if action == "sell":
        text = texts.get_crypto_sell_text(crypto, rate, network_fee_crypto, network_fee_rub)
    else:
        text = texts.get_crypto_buy_text(crypto, rate, network_fee_crypto, network_fee_rub)
    
    keyboard = texts.get_crypto_details_keyboard(action, crypto)
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()

# Обработчики для выбора криптовалют при продаже
async def sell_btc_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора BTC для продажи."""
    await _handle_crypto_selection(callback_query, state, "sell", "BTC")

async def sell_ltc_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора LTC для продажи."""
    await _handle_crypto_selection(callback_query, state, "sell", "LTC")

async def sell_trx_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора TRX для продажи."""
    await _handle_crypto_selection(callback_query, state, "sell", "TRX")

async def sell_usdt_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора USDT для продажи."""
    await _handle_crypto_selection(callback_query, state, "sell", "USDT")

# Обработчики для выбора криптовалют при покупке
async def buy_btc_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора BTC для покупки."""
    await _handle_crypto_selection(callback_query, state, "buy", "BTC")

async def buy_ltc_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора LTC для покупки."""
    await _handle_crypto_selection(callback_query, state, "buy", "LTC")

async def buy_trx_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора TRX для покупки."""
    await _handle_crypto_selection(callback_query, state, "buy", "TRX")

async def buy_usdt_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора USDT для покупки."""
    await _handle_crypto_selection(callback_query, state, "buy", "USDT")

# Обработчики для ввода суммы в рублях
async def _handle_rub_input(callback_query: CallbackQuery, state: FSMContext, action: str, crypto: str):
    """Общий обработчик ввода суммы в рублях.
    
    Args:
        callback_query: Callback query от нажатия кнопки "Ввести сумму в ₽"
        state: FSM состояние
        action: Действие ("sell" или "buy")
        crypto: Код криптовалюты
    """
    logger.info(f"Rub input handler called: action={action}, crypto={crypto}")
    
    rate, network_fee_crypto, network_fee_rub, _ = await _get_crypto_rate_and_fees(crypto)
    
    if not rate:
        await callback_query.message.answer(
            f"Ошибка получения курса {crypto}. Попробуйте позже.")
        await callback_query.answer()
        return
    
    # Переключаемся на ввод в рублях
    await state.update_data(action=action, crypto=crypto, input_mode="rub")
    await state.set_state(TransactionStates.waiting_for_rub_amount)
    
    text = texts.get_crypto_rub_text(action, crypto, rate, network_fee_crypto, network_fee_rub)
    keyboard = texts.get_rub_input_keyboard(action, crypto)
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()

# Обработчики для ввода суммы в рублях при продаже
async def sell_btc_rub_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик переключения на ввод суммы в рублях для продажи BTC."""
    logger.info("sell_btc_rub_handler called")
    await _handle_rub_input(callback_query, state, "sell", "BTC")

async def sell_ltc_rub_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик переключения на ввод суммы в рублях для продажи LTC."""
    logger.info("sell_ltc_rub_handler called")
    await _handle_rub_input(callback_query, state, "sell", "LTC")

async def sell_trx_rub_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик переключения на ввод суммы в рублях для продажи TRX."""
    logger.info("sell_trx_rub_handler called")
    await _handle_rub_input(callback_query, state, "sell", "TRX")

async def sell_usdt_rub_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик переключения на ввод суммы в рублях для продажи USDT."""
    logger.info("sell_usdt_rub_handler called")
    await _handle_rub_input(callback_query, state, "sell", "USDT")

# Обработчики для ввода суммы в рублях при покупке
async def buy_btc_rub_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик переключения на ввод суммы в рублях для покупки BTC."""
    logger.info("buy_btc_rub_handler called")
    await _handle_rub_input(callback_query, state, "buy", "BTC")

async def buy_ltc_rub_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик переключения на ввод суммы в рублях для покупки LTC."""
    logger.info("buy_ltc_rub_handler called")
    await _handle_rub_input(callback_query, state, "buy", "LTC")

async def buy_trx_rub_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик переключения на ввод суммы в рублях для покупки TRX."""
    logger.info("buy_trx_rub_handler called")
    await _handle_rub_input(callback_query, state, "buy", "TRX")

async def buy_usdt_rub_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик переключения на ввод суммы в рублях для покупки USDT."""
    logger.info("buy_usdt_rub_handler called")
    await _handle_rub_input(callback_query, state, "buy", "USDT")

# Обработчики для ввода суммы
async def handle_crypto_amount_input(message: Message, state: FSMContext):
    """Обработчик ввода суммы в криптовалюте.
    
    Args:
        message: Сообщение с суммой от пользователя
        state: FSM состояние
    """
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0. Попробуйте еще раз:")
            return
        
        # Получаем данные из состояния
        data = await state.get_data()
        action = data.get('action')
        crypto = data.get('crypto')
        input_mode = data.get('input_mode', 'crypto')
        
        if not action or not crypto:
            await message.answer("❌ Ошибка. Начните заново.")
            await state.clear()
            return
        
        # Сначала получаем курс для расчета сумм
        rate, _, _, _ = await _get_crypto_rate_and_fees(crypto)
        if not rate:
            await message.answer(f"❌ Ошибка получения курса {crypto}. Попробуйте позже.")
            await state.clear()
            return
        
        # В зависимости от режима ввода считаем вторую величину
        if input_mode == 'rub':
            amount_rub = amount
            amount_crypto = amount_rub / rate
        else:
            amount_crypto = amount
            amount_rub = amount_crypto * rate
        
        # Получаем комиссии (передаем сумму в рублях для расчета комиссии)
        _, network_fee_crypto, network_fee_rub, service_commission_rub = await _get_crypto_rate_and_fees(crypto, amount_rub)
        
        # Проверяем, что все значения получены корректно
        if network_fee_rub is None or service_commission_rub is None:
            await message.answer(f"❌ Ошибка получения комиссий для {crypto}. Попробуйте позже.")
            await state.clear()
            return
        
        # Рассчитываем итоговую сумму с комиссиями
        # Обе комиссии добавляются к итоговой сумме обмена
        total_amount = amount_rub + network_fee_rub + service_commission_rub
        
        # Сохраняем данные в состоянии
        await state.update_data(
            amount_crypto=amount_crypto,
            amount_rub=amount_rub,
            total_amount=total_amount,
            rate=rate,
            network_fee_rub=network_fee_rub,
            service_commission_rub=service_commission_rub
        )
        
        # Показываем расчёт и предлагаем выбрать способ получения оплаты
        from config import SERVICE_COMMISSION_PERCENT
        summary_text = texts.get_transaction_summary_text(
            action,
            crypto,
            amount_crypto,
            amount_rub,
            network_fee_crypto,
            network_fee_rub,
            service_commission_rub,
            SERVICE_COMMISSION_PERCENT,
        )
        await message.reply(summary_text, reply_markup=texts.get_payment_method_keyboard())
        await state.set_state(TransactionStates.waiting_for_payment_method)
        
    except ValueError:
        await message.answer("❌ Неверный формат суммы. Введите число (например: 0.001 или 1000):")

async def handle_rub_amount_input(message: Message, state: FSMContext):
    """Обработчик ввода суммы в рублях.
    
    Args:
        message: Сообщение с суммой от пользователя
        state: FSM состояние
    """
    try:
        amount_rub = float(message.text.replace(',', '.'))
        if amount_rub <= 0:
            await message.answer("❌ Сумма должна быть больше 0. Попробуйте еще раз:")
            return
        
        # Получаем данные из состояния
        data = await state.get_data()
        action = data.get('action')
        crypto = data.get('crypto')
        
        if not action or not crypto:
            await message.answer("❌ Ошибка. Начните заново.")
            await state.clear()
            return
        
        # Сначала получаем курс для расчета сумм
        rate, _, _, _ = await _get_crypto_rate_and_fees(crypto)
        if not rate:
            await message.answer(f"❌ Ошибка получения курса {crypto}. Попробуйте позже.")
            await state.clear()
            return
        
        # Рассчитываем сумму в криптовалюте
        amount_crypto = amount_rub / rate
        
        # Получаем комиссии (передаем сумму в рублях для расчета комиссии)
        _, network_fee_crypto, network_fee_rub, service_commission_rub = await _get_crypto_rate_and_fees(crypto, amount_rub)
        
        # Проверяем, что все значения получены корректно
        if network_fee_rub is None or service_commission_rub is None:
            await message.answer(f"❌ Ошибка получения комиссий для {crypto}. Попробуйте позже.")
            await state.clear()
            return
        
        # Рассчитываем итоговую сумму с комиссиями
        # Обе комиссии добавляются к итоговой сумме обмена
        total_amount = amount_rub + network_fee_rub + service_commission_rub
        
        # Сохраняем данные в состоянии
        await state.update_data(
            amount_crypto=amount_crypto,
            amount_rub=amount_rub,
            total_amount=total_amount,
            rate=rate,
            network_fee_rub=network_fee_rub,
            service_commission_rub=service_commission_rub
        )
        
        # Показываем расчет
        from config import SERVICE_COMMISSION_PERCENT
        summary_text = texts.get_transaction_summary_text(
            action,
            crypto,
            amount_crypto,
            amount_rub,
            network_fee_crypto,
            network_fee_rub,
            service_commission_rub,
            SERVICE_COMMISSION_PERCENT,
        )
        await message.reply(summary_text, reply_markup=texts.get_payment_method_keyboard())
        await state.set_state(TransactionStates.waiting_for_payment_method)
        
    except ValueError:
        await message.answer("❌ Неверный формат суммы. Введите число (например: 1000 или 50000):")

async def payment_sbp_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора СБП.
    
    Args:
        callback_query: Callback query от нажатия кнопки "СБП"
        state: FSM состояние
    """
    from config import SBP_PHONE, SBP_BANK, CRYPTO_WALLETS
    
    data = await state.get_data()
    action = data.get('action')
    crypto = data.get('crypto')
    amount_crypto = data.get('amount_crypto')
    amount_rub = data.get('amount_rub')
    total_amount = data.get('total_amount', amount_rub)  # Используем итоговую сумму с комиссиями
    
    # Проверяем, что все необходимые данные есть
    if not all([action, crypto, amount_crypto is not None, amount_rub is not None]):
        await callback_query.message.answer(
            "❌ Ошибка: не найдены данные транзакции. Начните заново."
        )
        await state.clear()
        await callback_query.answer()
        return
    
    if action == 'sell':
        # При ПРОДАЖЕ: показываем адрес кошелька для перевода крипты
        wallet_address = CRYPTO_WALLETS.get(crypto, "")
        
        if wallet_address:
            text = (
                f"💳 Продажа {crypto}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 Сумма: {amount_crypto:,.8f} {crypto}\n"
                f"💰 Вы получите: {amount_rub:,.2f} ₽\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📤 Адрес для отправки {crypto}:\n"
                f"`{wallet_address}`\n\n"
                f"Укажите ваш номер телефона и название банка для получения рублей\n"
                f"Пример: +79999999999, Сбербанк"
            )
        else:
            text = (
                f"💳 Продажа {crypto}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 Сумма: {amount_crypto:,.8f} {crypto}\n"
                f"💰 Вы получите: {amount_rub:,.2f} ₽\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📤 Адрес для отправки {crypto}: Временно не принимаем.\n\n"
                f"Укажите ваш номер телефона и название банка для получения рублей\n"
                f"Пример: +79999999999, Сбербанк"
            )
    else:
        # При ПОКУПКЕ: запрашиваем адрес кошелька пользователя
        text = (
            f"💳 Покупка {crypto}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 Сумма: {amount_crypto:,.8f} {crypto}\n"
            f"💰 Вы заплатите: {total_amount:,.2f} ₽\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📱 Реквизиты для оплаты:\n"
            f"Номер телефона: {SBP_PHONE}\n"
            f"Банк: {SBP_BANK}\n\n"
            f"Укажите адрес вашего {crypto} кошелька для получения криптовалюты\n"
            f"Пример: bc1qtmgxuhpqt5l36pwcrnh9ujkm0afgrqvgumnk0n"
        )
    
    await callback_query.message.reply(text, parse_mode="Markdown")
    await state.set_state(TransactionStates.waiting_for_phone)
    await callback_query.answer()

async def payment_operator_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора оператора для оплаты.
    
    Args:
        callback_query: Callback query от нажатия кнопки "Оператор"
        state: FSM состояние
    """
    from config import ADMIN_CHAT_ID
    
    # Получаем данные из состояния
    data = await state.get_data()
    action = data.get('action')
    crypto = data.get('crypto')
    amount_crypto = data.get('amount_crypto')
    amount_rub = data.get('amount_rub')
    total_amount = data.get('total_amount', amount_rub)
    
    if action and crypto and amount_crypto is not None and amount_rub is not None:
        # Если есть данные о транзакции, создаем заявку для оператора
        username = callback_query.from_user.username or callback_query.from_user.full_name or "Пользователь"
        user_id = callback_query.from_user.id
        
        # Определяем что запрашивать в зависимости от типа операции
        if action == 'sell':
            request_text = "Укажите ваш номер телефона и название банка для получения рублей\nПример: +79999999999, Сбербанк"
        else:
            request_text = f"Укажите адрес вашего {crypto} кошелька для получения криптовалюты\nПример: bc1qtmgxuhpqt5l36pwcrnh9ujkm0afgrqvgumnk0n"
        
        text = (
            f"👨‍💼 Связь с оператором\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💳 {action.title()} {crypto}\n"
            f"💎 Сумма: {amount_crypto:,.8f} {crypto}\n"
            f"💰 Сумма в рублях: {total_amount:,.2f} ₽\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{request_text}"
        )
        
        # Уведомляем админов о запросе оператора
        from utils.texts import format_user_display_name
        admin_text = (
            f"👤 *Пользователь запросил оператора:* {format_user_display_name(username)} (ID: {user_id})\n"
            f"💳 Операция: {action.title()} {crypto}\n"
            f"💎 Сумма: {amount_crypto:,.8f} {crypto}\n"
            f"💰 Сумма в рублях: {total_amount:,.2f} ₽\n\n"
            f"Свяжитесь с пользователем для завершения сделки."
        )
        
        admin_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💬 Ответить пользователю", callback_data=f"admin_reply_{user_id}")]
            ]
        )
        
        for admin_id in ADMIN_CHAT_ID:
            try:
                await callback_query.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    reply_markup=admin_keyboard,
                    parse_mode="Markdown"
                )
                logger.info(f"Operator request sent to admin {admin_id}")
            except (ConnectionError, TimeoutError, AiogramError) as e:
                logger.error(f"Failed to send operator request to admin {admin_id}: {e}")
        
        await callback_query.message.reply(text, parse_mode="Markdown")
        await state.set_state(TransactionStates.waiting_for_phone)
    else:
        # Если нет данных о транзакции, просто показываем контакт оператора
        await callback_query.message.answer(
            "👨‍💼 Связь с оператором: @jenya2hh\n\n"
            "Напишите оператору для получения помощи с обменом криптовалют.")
    
    await callback_query.answer()

async def phone_input_handler(message: Message, state: FSMContext):
    """Обработчик ввода данных пользователя.
    
    Args:
        message: Сообщение с данными пользователя (номер телефона/банк или адрес кошелька)
        state: FSM состояние
    """
    from utils.database import create_order
    from config import ADMIN_CHAT_ID
    
    user_input = message.text.strip()
    data = await state.get_data()
    action = data.get('action')
    crypto = data.get('crypto')
    amount_crypto = data.get('amount_crypto')
    amount_rub = data.get('amount_rub')
    total_amount = data.get('total_amount', amount_rub)  # Используем total_amount если есть, иначе amount_rub
    network_fee_rub = data.get('network_fee_rub', 0.0)
    service_commission_rub = data.get('service_commission_rub', 0.0)
    
    # Создаём заявку в БД (сохраняем итоговую сумму с комиссиями)
    username = message.from_user.username or message.from_user.full_name or "Пользователь"
    
    # В зависимости от типа операции сохраняем разные данные
    if action == 'sell':
        # При продаже: user_input содержит номер телефона и банк
        order_data = user_input
    else:
        # При покупке: user_input содержит адрес кошелька
        order_data = user_input
    
    order_number = await create_order(
        user_id=message.from_user.id,
        username=username,
        action=action,
        crypto=crypto,
        amount_crypto=amount_crypto,
        amount_rub=total_amount,  # Сохраняем итоговую сумму с комиссиями
        phone_and_bank=order_data
    )

    # Отправляем заявку пользователю (показываем итоговую сумму)
    final_text = texts.get_final_confirmation_text(action, crypto, amount_crypto, total_amount, order_data, order_number)
    await message.reply(final_text, reply_markup=texts.get_final_actions_keyboard())
    
    # Уведомляем админов (показываем итоговую сумму с комиссиями)
    admin_text, admin_keyboard = texts.get_admin_order_notification(
        order_number, action, crypto, amount_crypto, amount_rub, 
        order_data, username, message.from_user.id,
        service_commission=service_commission_rub,
        network_fee=network_fee_rub,
        total_amount=total_amount
    )
    
    for admin_id in ADMIN_CHAT_ID:
        try:
            await message.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_keyboard,
                parse_mode="Markdown"
            )
            logger.info(f"Order notification sent to admin {admin_id}")
        except (ConnectionError, TimeoutError, AiogramError) as e:
            logger.error(f"Failed to notify admin {admin_id} about order {order_number}: {e}")
    
    await state.clear()

async def cancel_transaction_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик отмены транзакции.
    
    Args:
        callback_query: Callback query от нажатия кнопки "Отмена"
        state: FSM состояние
    """
    await state.clear()
    
    # Удаляем текущее сообщение
    try:
        await callback_query.message.delete()
    except (ConnectionError, TimeoutError) as e:
        logger.warning(f"Could not delete message: {e}")
    
    # Показываем стартовое меню
    from handlers.main import start_handler
    await start_handler(callback_query)

async def cancel_order_handler(callback_query: CallbackQuery):
    """Обработчик отмены заявки.
    
    Args:
        callback_query: Callback query от нажатия кнопки "Отменить заявку"
    """
    # Удаляем текущее сообщение
    try:
        await callback_query.message.delete()
    except (ConnectionError, TimeoutError) as e:
        logger.warning(f"Could not delete message: {e}")
    
    # Показываем стартовое меню
    from handlers.main import start_handler
    await start_handler(callback_query)
    await callback_query.answer("Заявка отменена")

async def send_tx_link_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик отправки ссылки на транзакцию.
    
    Args:
        callback_query: Callback query от нажатия кнопки "Отправить ссылку на транзакцию"
        state: FSM состояние
    """
    await state.set_state(TransactionStates.waiting_for_tx_link)
    await callback_query.message.answer(
        "📎 Отправьте ссылку на транзакцию в блокчейне.\n"
        "После отправки ссылки оператор проверит транзакцию и обработает заявку."
    )
    await callback_query.answer()

async def tx_link_input_handler(message: Message, state: FSMContext):
    """Обработчик ввода ссылки на транзакцию.
    
    Args:
        message: Сообщение со ссылкой на транзакцию
        state: FSM состояние
    """
    from config import ADMIN_CHAT_ID
    
    tx_link = message.text.strip()
    username = message.from_user.username or message.from_user.full_name or "Пользователь"
    user_id = message.from_user.id
    
    # Подтверждаем пользователю
    await message.reply("✅ Ссылка на транзакцию получена. Оператор проверит её и свяжется с вами.")
    
    # Отправляем ссылку админам
    from utils.texts import format_user_display_name
    admin_text = (
        f"👤 *Пользователь:* {format_user_display_name(username)} (ID: {user_id})\n"
        f"🔗 `{tx_link}`\n\n"
        f"Проверьте транзакцию и свяжитесь с пользователем."
    )
    
    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Ответить пользователю", callback_data=f"admin_reply_{user_id}")]
        ]
    )
    
    for admin_id in ADMIN_CHAT_ID:
        try:
            await message.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_keyboard,
                parse_mode="Markdown"
            )
            logger.info(f"Transaction link sent to admin {admin_id}")
        except AiogramError as e:  # <-- ИЗМЕНЕНИЕ ЗДЕСЬ
            # Ловим любую ошибку API Aiogram, включая 'chat not found'
            logger.error(f"Failed to send transaction link to admin {admin_id}: {e}")
            logger.warning(f"Possible reason: Admin {admin_id} has not started the bot yet.")
    
    await state.clear()

async def reply_to_operator_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик кнопки "Ответить оператору".
    
    Args:
        callback_query: Callback query от нажатия кнопки "Ответить оператору"
        state: FSM состояние
    """
    await callback_query.message.answer(
        "💬 Отправьте ваше сообщение для оператора:\n\n"
        "Опишите ваш вопрос или проблему, и оператор свяжется с вами в ближайшее время."
    )
    await state.set_state(TransactionStates.waiting_for_operator_reply)
    await callback_query.answer()

async def operator_reply_input_handler(message: Message, state: FSMContext):
    """Обработчик ввода ответа оператору.
    
    Args:
        message: Сообщение с ответом оператору
        state: FSM состояние
    """
    from config import ADMIN_CHAT_ID
    
    user_reply = message.text.strip()
    username = message.from_user.username or message.from_user.full_name or "Пользователь"
    user_id = message.from_user.id
    
    # Подтверждаем пользователю
    await message.reply("✅ Ваше сообщение отправлено оператору. Ожидайте ответа.")
    
    # Отправляем сообщение админам
    from utils.texts import format_user_display_name
    admin_text = (
        f"💬 *Ответ от пользователя:* {format_user_display_name(username)} (ID: {user_id})\n\n"
        f"📝 Сообщение:\n{user_reply}\n\n"
        f"Ответьте пользователю, используя кнопку ниже."
    )
    
    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Ответить пользователю", callback_data=f"admin_reply_{user_id}")]
        ]
    )
    
    for admin_id in ADMIN_CHAT_ID:
        try:
            await message.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_keyboard,
                parse_mode="Markdown"
            )
            logger.info(f"User reply sent to admin {admin_id}")
        except (ConnectionError, TimeoutError, AiogramError) as e:
            logger.error(f"Failed to send user reply to admin {admin_id}: {e}")
    
    await state.clear()

async def debug_callback_handler(callback_query: CallbackQuery):
    """Отладочный обработчик для всех callback-ов.
    
    Args:
        callback_query: Callback query для отладки
    """
    logger.info(f"Debug callback received: {callback_query.data}")
    await callback_query.message.answer(f"🔍 DEBUG: Получен callback с данными: {callback_query.data}")
    await callback_query.answer()
