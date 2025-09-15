from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Tuple

# Импортируем наши фабрики колбеков
from .callbacks import CryptoInputSwitch, CryptoSelection, RubInputSwitch

def format_user_display_name(username: str) -> str:
    """Форматирует имя пользователя для отображения."""
    if not username or username in ["Пользователь", "Нет username"]:
        return "Пользователь"
    
    if ' ' not in username and not username.startswith('@'):
        return f"@{username}"
    
    return username

# --- Константы для главного меню ---
WELCOME_PHOTO_URL = "AgACAgIAAxkBAAOCaMe8_YoQvR8VmQgxGrvwJ2Ew8bQAAqP4MRvD4zhKhf8sL6uWlyABAAMCAAN5AAM2BA"

WELCOME_TEXT = (
    "👋 *Добро пожаловать в ExpressObmen P2P!*\n\n"
    "💸 *Обмен криптовалюты без лишних комиссий и задержек!*\n"
    "⚡️ *Самые низкие комиссии на рынке* — мы заботимся о вашем бюджете!\n"
    "🔒 *Безопасные транзакции* и гарантия надежности.\n"
    "🚀 *Моментальные обмены 24/7* в пару кликов.\n"
    "📱 *Удобный интерфейс прямо в Telegram* — просто выберите валюту и сумму!\n\n"
    "*Начните обмен прямо сейчас* и ощутите скорость и выгоду с *ExpressObmen P2P!*\n\n"
)

HELP_TEXT = "памагите"

# --- Функции для генерации клавиатур ---

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Возвращает главную клавиатуру с кнопками."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Купить крипту", callback_data="buy"),
                InlineKeyboardButton(text="💸 Продать крипту", callback_data="sell"),
            ],
            [
                InlineKeyboardButton(text="👨‍💼 Оператор", url="https://t.me/jenya2hh"),
                InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            ],
            [
                InlineKeyboardButton(text="🎁 Активировать промокод", callback_data="activate_promo"),
            ],
            [
                InlineKeyboardButton(text="⭐ Отзывы", url="https://t.me/ExpressObmenChannel"),
            ],
        ]
    )
    return keyboard

def get_back_to_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Универсальная клавиатура для возврата в главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="main_menu")]
        ]
    )

def get_crypto_selection_keyboard(action: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора криптовалюты, используя CallbackData."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟡 Bitcoin (BTC)", callback_data=CryptoSelection(action=action, crypto="BTC").pack()),
                InlineKeyboardButton(text="⚡️ Litecoin (LTC)", callback_data=CryptoSelection(action=action, crypto="LTC").pack())
            ],
            [
                InlineKeyboardButton(text="🔷 TRON (TRX)", callback_data=CryptoSelection(action=action, crypto="TRX").pack()),
                InlineKeyboardButton(text="💵 Tether (USDT)", callback_data=CryptoSelection(action=action, crypto="USDT").pack())
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ]
    )
    return keyboard

def get_crypto_details_keyboard(action: str, crypto: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для переключения на ввод в рублях."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Ввести сумму в ₽", callback_data=RubInputSwitch(action=action, crypto=crypto).pack())
            ],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel_transaction")]
        ]
    )
    return keyboard

def get_rub_input_keyboard(action: str, crypto: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для возврата к вводу в криптовалюте."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🔄 Ввести сумму в {crypto}", 
                    callback_data=CryptoInputSwitch(action=action, crypto=crypto).pack()
                )
            ],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel_transaction")]
        ]
    )
    return keyboard

def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора способа оплаты."""
    rows = [
        [InlineKeyboardButton(text="💳 СБП", callback_data="payment_sbp")],
        [InlineKeyboardButton(text="👨‍💼 Через оператора", callback_data="payment_operator")],
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel_transaction")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_final_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру после создания заявки (ИСПРАВЛЕННАЯ ВЕРСИЯ).
    Кнопка отмены теперь содержит ID заявки.
    """
    rows = [
        # --- ИЗМЕНЕНИЕ ЗДЕСЬ ---
        [InlineKeyboardButton(text="❌ Отменить заявку", callback_data=f"cancel_order_{order_id}")],
        [InlineKeyboardButton(text="👨‍💼 Связаться с оператором", url="https://t.me/jenya2hh")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_admin_reply_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру с кнопкой "Ответить пользователю" для админа."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Ответить пользователю", callback_data=f"admin_reply_{user_id}")]
        ]
    )
def get_reply_to_operator_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для ответа оператору (добавляется к сообщениям от оператора)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Ответить оператору", callback_data="reply_to_operator")]
        ]
    )

# --- Функции для генерации текстов сообщений ---

SELL_CRYPTO_TEXT = "*🧾 Меню продажи*\n\nВыберите криптовалюту для продажи и следуйте подсказкам."
BUY_CRYPTO_TEXT = "*🧾 Меню покупки*\n\nВыберите криптовалюту для покупки и следуйте подсказкам."
OPERATOR_CONTACT_TEXT = "👨‍💼 *Связь с оператором:* @jenya2hh\n\nНапишите оператору для получения помощи с обменом."
SEND_TX_LINK_PROMPT = "📎 *Отправьте ссылку на транзакцию в блокчейне.*\n\nПосле отправки оператор проверит ее и обработает заявку."
REPLY_TO_OPERATOR_PROMPT = "💬 *Отправьте ваше сообщение для оператора:*"

def get_crypto_prompt_text(action: str, crypto: str, rate: float) -> str:
    """Возвращает универсальный текст с предложением ввести сумму в криптовалюте."""
    if action == 'sell':
        action_text = f"*Продажа {crypto}*"
        prompt_text = f"Пожалуйста, введите сумму в *{crypto}*, которую вы хотите продать."
    else:
        action_text = f"*Покупка {crypto}*"
        prompt_text = f"Пожалуйста, введите сумму в *{crypto}*, которую вы хотите купить."

    formatted_rate = f"{rate:,.2f}".replace(",", " ")
    return (
        f"{action_text}\n\n"
        f"Текущий курс: `1 {crypto} ≈ {formatted_rate} RUB`\n\n"
        f"{prompt_text}"
    )

def get_rub_prompt_text(action: str, crypto: str, rate: float) -> str:
    """Возвращает универсальный текст с предложением ввести сумму в рублях."""
    if action == 'sell':
        action_text = f"*Продажа {crypto}*"
        prompt_text = f"Пожалуйста, введите сумму в *RUB*, на которую вы хотите продать *{crypto}*."
    else:
        action_text = f"*Покупка {crypto}*"
        prompt_text = f"Пожалуйста, введите сумму в *RUB*, на которую вы хотите купить *{crypto}*."

    formatted_rate = f"{rate:,.2f}".replace(",", " ")
    return (
        f"{action_text}\n\n"
        f"Текущий курс: `1 {crypto} ≈ {formatted_rate} RUB`\n\n"
        f"{prompt_text}"
    )

def get_transaction_summary_text(
    action: str, crypto: str, amount_crypto: float, amount_rub: float,
    total_amount: float, service_commission_rub: float, network_fee_rub: float,
    promo_applied: bool
) -> str:
    """Формирует итоговый текст с расчетом транзакции для подтверждения."""
    amount_crypto_str = f"{amount_crypto:,.8f}".rstrip('0').rstrip('.')
    amount_rub_str = f"{amount_rub:,.2f}".replace(",", " ")
    service_commission_str = f"{service_commission_rub:,.2f}".replace(",", " ")
    network_fee_str = f"{network_fee_rub:,.2f}".replace(",", " ")
    total_amount_str = f"{total_amount:,.2f}".replace(",", " ")

    action_title = f"*Подтвердите продажу {crypto}*" if action == 'sell' else f"*Подтвердите покупку {crypto}*"
    final_line_title = "Итого к получению:" if action == 'sell' else "Итого к оплате:"

    details = [
        f"💎 *Сумма в {crypto}:* `{amount_crypto_str}`",
        f"💰 *Эквивалент в рублях:* `{amount_rub_str} RUB`"
    ]

    if promo_applied:
        details.append("\n✅ *Промокод применен*")
        details.append(f"  - Комиссия сервиса: `0.00 RUB`")
        details.append(f"  - Комиссия сети: `0.00 RUB`")
    else:
        details.append("\n🧾 *Комиссии*")
        details.append(f"  - Комиссия сервиса: `{service_commission_str} RUB`")
        details.append(f"  - Комиссия сети: `{network_fee_str} RUB`")

    details_str = "\n".join(details)
    return (
        f"{action_title}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{details_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*{final_line_title}* `{total_amount_str} RUB`\n\n"
        f"Выберите способ оплаты/получения:"
    )

def get_sbp_sell_details_text(crypto: str, amount_crypto: float, amount_rub: float, wallet_address: str) -> str:
    """Текст для пользователя при продаже через СБП."""
    amount_crypto_str = f"{amount_crypto:,.8f}".rstrip('0').rstrip('.')
    amount_rub_str = f"{amount_rub:,.2f}".replace(",", " ")
    
    if wallet_address:
        wallet_line = f"`{wallet_address}`"
    else:
        wallet_line = "Временно не принимаем."
        
    return (
        f"💳 *Продажа {crypto}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 *Сумма:* `{amount_crypto_str} {crypto}`\n"
        f"💰 *Вы получите:* `{amount_rub_str} RUB`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📤 *Адрес для отправки {crypto}:*\n"
        f"{wallet_line}\n\n"
        f"Укажите ваш номер телефона и название банка для получения рублей\n"
        f"*Пример:* `+79991234567, Сбербанк`"
    )

def get_sbp_buy_details_text(crypto: str, amount_crypto: float, total_amount: float, sbp_phone: str, sbp_bank: str) -> str:
    """Текст для пользователя при покупке через СБП."""
    amount_crypto_str = f"{amount_crypto:,.8f}".rstrip('0').rstrip('.')
    total_amount_str = f"{total_amount:,.2f}".replace(",", " ")
    
    return (
        f"💳 *Покупка {crypto}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 *Вы получите:* `{amount_crypto_str} {crypto}`\n"
        f"💰 *К оплате:* `{total_amount_str} RUB`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 *Реквизиты для оплаты:*\n"
        f"  - Номер телефона: `{sbp_phone}`\n"
        f"  - Банк: *{sbp_bank}*\n\n"
        f"Укажите адрес вашего *{crypto}* кошелька для получения криптовалюты."
    )

def get_final_confirmation_text(
    action: str, crypto: str, amount_crypto: float,
    total_amount: float, user_input: str, order_number: int
) -> str:
    """Финальное подтверждение для пользователя после создания заявки."""
    direction = "Продажа" if action == "sell" else "Покупка"
    final_amount_str = f"{total_amount:,.2f}".replace(",", " ")
    
    return (
        f"✅ *Заявка #{order_number} на {direction.lower()} создана! Оператор скоро с вами свяжется.*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 *Сумма:* `{f'{amount_crypto:,.8f}'.rstrip('0').rstrip('.')} {crypto}`\n"
        f"💰 *Итоговая сумма:* `{final_amount_str} RUB`\n"
        f"📝 *Ваши реквизиты:* `{user_input}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Ожидайте подтверждения от оператора."
    )

def get_admin_order_notification(
    order_id: int,
    order_number: int,
    user_id: int,
    username: str,
    order_data: dict,
    user_input: str
) -> Tuple[str, InlineKeyboardMarkup]:
    """
    Формирует уведомление для админа о новой заявке (ФИНАЛЬНАЯ ВЕРСИЯ).
    Принимает и order_id (для кнопок), и order_number (для текста).
    """
    action = order_data.get('action', 'N/A').title()
    crypto = order_data.get('crypto', 'N/A')
    
    # Форматирование числовых значений для красивого вывода
    amount_crypto_str = f"{order_data.get('amount_crypto', 0):,.8f}".rstrip('0').rstrip('.')
    amount_rub_str = f"{order_data.get('amount_rub', 0):,.2f}".replace(",", " ")
    service_commission_str = f"{order_data.get('service_commission_rub', 0):,.2f}".replace(",", " ")
    network_fee_str = f"{order_data.get('network_fee_rub', 0):,.2f}".replace(",", " ")
    total_amount_str = f"{order_data.get('total_amount', 0):,.2f}".replace(",", " ")
    
    user_details_title = "Реквизиты для получения RUB:" if order_data.get('action') == 'sell' else f"Адрес кошелька {crypto}:"

    # Формируем список с деталями заявки
    details = [
        f"👤 *Пользователь:* {format_user_display_name(username)} (`{user_id}`)",
        f"\n*Детали заявки:*",
        f"  - *Тип:* {action} {crypto}",
        f"  - *Сумма в крипте:* `{amount_crypto_str} {crypto}`",
        f"  - *Эквивалент в RUB (чистыми):* `{amount_rub_str} RUB`",
        f"\n*Комиссии:*",
        f"  - *Сервис:* `{service_commission_str} RUB`",
        f"  - *Сеть:* `{network_fee_str} RUB`",
        f"\n*Итоговая сумма:* `{total_amount_str} RUB`",
        f"\n*{user_details_title}*",
        f"`{user_input}`"
    ]
    
    # Если был применен промокод, добавляем плашку
    if order_data.get('promo_applied'):
        details.insert(1, "✅ *ИСПОЛЬЗОВАН ПРОМОКОД*")

    # Безопасно объединяем детали в одну строку
    details_str = "\n".join(details)
    
    # Формируем основной текст, используя "красивый" номер заявки
    admin_text = (
        f"🔔 *Новая заявка #{order_number}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{details_str}"
    )

    # Создаем клавиатуру, используя реальный, уникальный order_id для callback_data
    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_order_{order_id}_{user_id}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data=f"reject_order_{order_id}_{user_id}")
            ],
            [InlineKeyboardButton(text="💬 Ответить пользователю", callback_data=f"admin_reply_{user_id}")]
        ]
    )
    
    return admin_text, admin_keyboard


def get_operator_request_texts(username: str, user_id: int, data: dict) -> Tuple[str, str]:
    """Генерирует тексты для запроса оператора."""
    action = data.get('action', '').title()
    crypto = data.get('crypto', '')
    amount_crypto = data.get('amount_crypto', 0)
    total_amount = data.get('total_amount', 0)

    user_text = (
        f"👨‍💼 *Ваша заявка передана оператору.*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Пожалуйста, укажите ваши реквизиты в следующем сообщении.\n\n"
        f"*Пример для продажи:* `+79991234567, Сбербанк`\n"
        f"*Пример для покупки:* `bc1q...`"
    )

    admin_text = (
        f"👨‍💼 *Пользователь запросил оператора*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Пользователь:* {format_user_display_name(username)} (`{user_id}`)\n"
        f"💳 *Операция:* {action} {crypto}\n"
        f"💎 *Сумма:* `{f'{amount_crypto:,.8f}'.rstrip('0').rstrip('.')} {crypto}`\n"
        f"💰 *Итоговая сумма:* `{total_amount:,.2f} RUB`\n\n"
        f"Свяжитесь с пользователем для завершения сделки."
    )
    return user_text, admin_text


def get_tx_link_notification(username: str, user_id: int, tx_link: str) -> Tuple[str, InlineKeyboardMarkup]:
    """Уведомление для админа о ссылке на транзакцию."""
    admin_text = (
        f"🔗 *Ссылка на транзакцию от пользователя*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Пользователь:* {format_user_display_name(username)} (`{user_id}`)\n\n"
        f"`{tx_link}`\n\n"
        f"Проверьте транзакцию и свяжитесь с пользователем."
    )
    return admin_text, get_admin_reply_keyboard(user_id)


def get_user_reply_notification(username: str, user_id: int, user_reply: str) -> Tuple[str, InlineKeyboardMarkup]:
    """Уведомление для админа о сообщении от пользователя."""
    admin_text = (
        f"💬 *Сообщение от пользователя*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Пользователь:* {format_user_display_name(username)} (`{user_id}`)\n\n"
        f"📝 *Текст:*\n{user_reply}"
    )
    return admin_text, get_admin_reply_keyboard(user_id)