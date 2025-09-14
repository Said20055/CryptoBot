from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def format_user_display_name(username: str) -> str:
    """Форматирует имя пользователя для отображения.
    
    Args:
        username: username или полное имя пользователя
        
    Returns:
        Отформатированное имя с @ для username или без @ для полного имени
    """
    if not username or username == "Пользователь":
        return "Пользователь"
    
    # Если это username (без пробелов и не начинается с @), добавляем @
    if ' ' not in username and not username.startswith('@'):
        return f"@{username}"
    
    # Иначе это полное имя, возвращаем как есть
    return username

# Контент приветственного экрана
WELCOME_PHOTO_URL = "https://postimg.cc/LhjTfzJd"

WELCOME_TEXT = (
    "Добро пожаловать в крипто-обменник! 🚀\n\n"
    "Выберите действие ниже, чтобы начать обмен с оператором."
)

# Основное меню с кнопками
MAIN_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Купить крипту", callback_data="buy"),
        ],
        [
            InlineKeyboardButton(text="💸 Продать крипту", callback_data="sell"),
            InlineKeyboardButton(text="👨‍💼 Оператор", url="https://t.me/jenya2hh"),
            InlineKeyboardButton(text="⭐ Отзывы", url="https://t.me/Blockchain_Exchange_Btc"),
        ],
    ]
)

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Совместимость со старыми импортами: вернуть основную клавиатуру."""
    return MAIN_KEYBOARD

# =====================
# Тексты и клавиатуры для обменов
# =====================

SELL_CRYPTO_TEXT = (
    "🧾 Меню продажи\n\n"
    "Выберите криптовалюту для продажи и следуйте подсказкам."
)

BUY_CRYPTO_TEXT = (
    "🧾 Меню покупки\n\n"
    "Выберите криптовалюту для покупки и следуйте подсказкам."
)

def _crypto_callback(action: str, crypto: str) -> str:
    return f"{action}_{crypto.lower()}"

def _crypto_rub_callback(action: str, crypto: str) -> str:
    return f"{action}_{crypto.lower()}_rub"

def get_crypto_selection_keyboard(action: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора криптовалюты для действий sell/buy."""
    rows = [
        [
            InlineKeyboardButton(text="🟡 BTC", callback_data=_crypto_callback(action, "BTC")),
            InlineKeyboardButton(text="⚡ LTC", callback_data=_crypto_callback(action, "LTC")),
        ],
        [
            InlineKeyboardButton(text="🔷 TRX", callback_data=_crypto_callback(action, "TRX")),
            InlineKeyboardButton(text="💵 USDT", callback_data=_crypto_callback(action, "USDT")),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_crypto_details_keyboard(action: str, crypto: str) -> InlineKeyboardMarkup:
    """Клавиатура после выбора монеты: переход к вводу суммы в рублях."""
    rows = [
        [InlineKeyboardButton(text="💵 Ввести сумму в ₽", callback_data=_crypto_rub_callback(action, crypto))],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=action)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_rub_input_keyboard(action: str, crypto: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="₿ Ввести сумму в криптовалюте", callback_data=_crypto_callback(action, crypto))],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=action)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_crypto_sell_text(crypto: str, rate: float, network_fee_crypto: float, network_fee_rub: float) -> str:
    from config import SERVICE_COMMISSION_PERCENT
    return (
        f"🟦 Продажа {crypto}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📉 Курс продажи: {rate:,.2f} ₽\n"
        f"🔗 Сеть: {crypto}\n"
        f"💼 Комиссия сервиса: {SERVICE_COMMISSION_PERCENT:.1f}%\n"
        f"⚙️ Комиссия сети: {network_fee_crypto} {crypto} ({network_fee_rub:,.2f} ₽)\n"
        f"⚠️ Обе комиссии добавляются к итоговой сумме\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✉️ Введите сумму в {crypto}"
    )

def get_crypto_buy_text(crypto: str, rate: float, network_fee_crypto: float, network_fee_rub: float) -> str:
    from config import SERVICE_COMMISSION_PERCENT
    return (
        f"🟩 Покупка {crypto}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 Курс покупки: {rate:,.2f} ₽\n"
        f"🔗 Сеть: {crypto}\n"
        f"💼 Комиссия сервиса: {SERVICE_COMMISSION_PERCENT:.1f}%\n"
        f"⚙️ Комиссия сети: {network_fee_crypto} {crypto} ({network_fee_rub:,.2f} ₽)\n"
        f"⚠️ Обе комиссии добавляются к итоговой сумме\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✉️ Введите сумму в {crypto}"
    )

def get_crypto_rub_text(action: str, crypto: str, rate: float, network_fee_crypto: float, network_fee_rub: float) -> str:
    from config import SERVICE_COMMISSION_PERCENT
    verb = "продать" if action == "sell" else "купить"
    return (
        f"🧾 Сумма в рублях\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Вы хотите {verb} {crypto}.\n"
        f"Текущий курс: {rate:,.2f} ₽ за 1 {crypto}\n"
        f"💼 Комиссия сервиса: {SERVICE_COMMISSION_PERCENT:.1f}%\n"
        f"⚙️ Комиссия сети: {network_fee_crypto} {crypto} ({network_fee_rub:,.2f} ₽)\n"
        f"⚠️ Обе комиссии добавляются к итоговой сумме\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✉️ Отправьте сумму в ₽ сообщением."
    )

def get_transaction_summary_text(
    action: str,
    crypto: str,
    amount_crypto: float,
    amount_rub: float,
    network_fee_crypto: float,
    network_fee_rub: float,
    commission_rub: float,
    commission_percent: float = 0.0,
) -> str:
    verb_inf = "продать" if action == "sell" else "купить"
    total_caption = "к получению" if action == "sell" else "к оплате"
    
    # Рассчитываем итоговую сумму с обеими комиссиями
    total_receive = amount_rub + network_fee_rub + commission_rub
    
    # Рассчитываем процент комиссии сервиса
    if commission_rub > 0 and amount_rub > 0:
        actual_commission_percent = (commission_rub / amount_rub) * 100
    else:
        actual_commission_percent = 0.0
    
    return (
        f"Вы хотите {verb_inf} {amount_crypto:,.8f} {crypto}\n"
        f"Сумма в рублях: {amount_rub:,.2f} ₽\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔸 Комиссия сети: ({network_fee_rub:,.2f} ₽)\n"
        f"📊 Комиссия сервиса ({actual_commission_percent:.2f}%): {commission_rub:,.2f} ₽\n"
        f"💵 Итого {total_caption}: {total_receive:,.2f} ₽\n"
        f"━━━━━━━━━━━━━━━━\n"
    )

def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="💳 СБП", callback_data="payment_sbp")],
        [InlineKeyboardButton(text="👨‍💼 Оператор", url="https://t.me/jenya2hh")],
        [InlineKeyboardButton(text="« Отмена", callback_data="cancel_transaction")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_phone_request_text(action: str, crypto: str, amount_crypto: float, amount_rub: float) -> str:
    verb = "Продажа" if action == "sell" else "Покупка"
    return (
        f"💳 {verb} {crypto}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 Сумма: {amount_crypto:,.8f} {crypto}\n"
        f"💰 Вы получите: {amount_rub:,.2f} ₽\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Укажите  Номер телефона и название банка\n"
        f"Пример: +79999999999, Сбербанк, можно ввести номер карты \n"
        f"но комиссия банка берется из вашей суммы."
    )

def get_final_confirmation_text(
    action: str,
    crypto: str,
    amount_crypto: float,
    amount_rub: float,
    phone_and_bank: str,
    order_number: int,
) -> str:
    from config import CRYPTO_WALLETS
    
    direction = "Продажа" if action == "sell" else "Покупка"
    you_phrase = "Вы получите" if action == "sell" else "Вы заплатите"
    
    wallet_address = CRYPTO_WALLETS.get(crypto, "")
    
    text = (
        f"✅ Заявка на {direction.lower()} #{order_number} создана!\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💰 Сумма {direction.lower()}: {amount_crypto:,.8f} {crypto}\n"
        f"💵 {you_phrase}: {amount_rub:,.2f} ₽\n"
        f"💳 Способ получения: sbp\n"
        f"📝 Ваши реквизиты: {phone_and_bank}\n"
        f"━━━━━━━━━━━━━━━━\n"
    )
      
    return text

def get_final_actions_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="❌ Отменить заявку", callback_data="cancel_order")],
        [InlineKeyboardButton(text="👨‍💼 Оператор", url="https://t.me/jenya2hh")],
        #[InlineKeyboardButton(text="📎 Отправить ссылку на транзакцию", callback_data="send_tx_link")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_reply_to_operator_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для ответа оператору (добавляется к сообщениям от оператора)"""
    rows = [
        [InlineKeyboardButton(text="💬 Ответить оператору", callback_data="reply_to_operator")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_admin_order_notification(
    order_number: int,
    action: str,
    crypto: str,
    amount_crypto: float,
    amount_rub: float,
    phone_and_bank: str,
    username: str,
    user_id: int,
    service_commission: float = 0.0,
    network_fee: float = 0.0,
    total_amount: float = None,
) -> tuple[str, InlineKeyboardMarkup]:
    """Уведомление для админов о новой заявке"""
    direction = "Продажа" if action == "sell" else "Покупка"
    you_phrase = "получит" if action == "sell" else "заплатит"
    
    # Экранируем специальные символы для Markdown
    safe_phone = phone_and_bank.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
    safe_username = username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
    
    # Форматируем имя пользователя для отображения
    display_name = format_user_display_name(safe_username)
    
    # Если total_amount не передан, используем amount_rub
    if total_amount is None:
        total_amount = amount_rub
    
    # Рассчитываем процент комиссии сервиса
    if service_commission > 0 and amount_rub > 0:
        commission_percent = (service_commission / amount_rub) * 100
    else:
        commission_percent = 0.0
    
    text = (
        f"🔔 *Новая заявка #{order_number}*\n\n"
        f"👤 *Пользователь:* {display_name} (ID: {user_id})\n"
        f"💰 *{direction}:* {amount_crypto:,.8f} {crypto}\n"
        f"💵 *Сумма обмена:* {amount_rub:,.2f} ₽\n"
        f"📊 *Комиссия сервиса ({commission_percent:.2f}%):* {service_commission:,.2f} ₽\n"
        f"🔸 *Комиссия сети:* {network_fee:,.2f} ₽\n"
        f"💳 *Итого {you_phrase}:* {total_amount:,.2f} ₽\n"
        f"💳 *Способ получения:* sbp\n"
        f"📝 *Реквизиты:* {safe_phone}"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Ответить пользователю", callback_data=f"admin_reply_{user_id}")]
        ]
    )
    
    return text, keyboard

HELP_TEXT = "памагите"
