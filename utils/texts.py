import html

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
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
                InlineKeyboardButton(text="⭐ Отзывы", url="https://t.me/+obvt9s7jKgYzNzUy"),
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

def get_final_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Все верно, получить реквизиты", callback_data="final_confirm_and_get_requisites")
    builder.button(text="❌ Отменить", callback_data="cancel_transaction")
    builder.adjust(1)
    return builder.as_markup()

def get_final_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить заявку", callback_data=f"cancel_order_{order_id}")
    return builder.as_markup()




def get_persistent_reply_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура, которая управляет сессией ответа (начать/закончить).
    Используется для того, чтобы один клик открывал сессию обмена сообщениями без необходимости
    нажимать кнопку для каждого сообщения.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Завершить переписку", callback_data="end_reply_session")]
    ])

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
    promo_applied: bool, user_requisites: str # <-- НОВЫЙ ПАРАМЕТР
) -> str:
    """
    (ИЗМЕНЕНО) Формирует текст с полным обзором транзакции, включая реквизиты пользователя.
    """
    commission_info = "Без комиссии ✨" if promo_applied else f"{service_commission_rub:.2f} RUB"
    network_fee_info = "Покрывается нами" if promo_applied else f"{network_fee_rub:.2f} RUB"
    
    if action == 'buy':
        requisites_title = "Ваш кошелек для получения"
        total_line = f"<b>К оплате:</b> <code>{total_amount:.2f} RUB</code>"
    else: # sell
        requisites_title = "Ваши реквизиты для получения"
        total_line = f"<b>К получению:</b> <code>{total_amount:.2f} RUB</code>"

    # Безопасно экранируем ввод пользователя
    safe_user_requisites = html.escape(user_requisites)

    return (
        f"<b>🔍 Пожалуйста, проверьте все данные:</b>\n\n"
        f"<b>Действие:</b> {'Покупка' if action == 'buy' else 'Продажа'} {crypto.upper()}\n"
        f"<b>Сумма в криптовалюте:</b> <code>{amount_crypto:.8f} {crypto.upper()}</code>\n"
        f"<b>Сумма в рублях:</b> <code>{amount_rub:.2f} RUB</code>\n\n"
        f"<b>{requisites_title}:</b>\n"
        f"<code>{safe_user_requisites}</code>\n\n"
        f"<b>Комиссия сервиса:</b> {commission_info}\n"
        f"<b>Комиссия сети:</b> {network_fee_info}\n\n"
        f"{total_line}\n\n"
        f"Если все верно, нажмите кнопку ниже."
    )

def get_user_requisites_prompt_text(action: str, crypto: str) -> str:
    """
    Возвращает текст с просьбой ввести реквизиты.
    Текст зависит от того, покупает пользователь крипту или продает.
    """
    if action == 'buy':
        # Если покупает, просим адрес его кошелька
        prompt = (
            f"✅ <b>Отлично!</b>\n\n"
            f"Теперь, пожалуйста, отправьте <b>адрес вашего {crypto.upper()} кошелька</b>, "
            f"на который мы отправим криптовалюту после получения вашей оплаты."
        )
    else: # sell
        # Если продает, просим банковские реквизиты
        prompt = (
            "✅ <b>Отлично!</b>\n\n"
            "Теперь, пожалуйста, отправьте сообщение с вашими реквизитами для получения оплаты. "
            "Например:\n"
            "<code>Иванов Иван Иванович, Сбербанк, 89991234567</code>"
        )
    return prompt

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




def get_admin_order_notification_for_topic(
    order_id: int,
    order_number: int,
    user_id: int,
    username: str,
    order_data: dict,
    user_input: str
) -> Tuple[str, InlineKeyboardMarkup]:
    """
    Формирует HTML-текст с деталями заявки для отправки в тему группы.
    Возвращает текст (str) и клавиатуру (InlineKeyboardMarkup).
    """
    # Безопасно извлекаем данные из словаря FSM
    action = order_data.get('action', 'N/A').title()
    crypto = order_data.get('crypto', 'N/A')

    # Форматируем все числовые значения для красивого вывода
    amount_crypto_str = f"{order_data.get('amount_crypto', 0):,.8f}".rstrip('0').rstrip('.')
    amount_rub_str = f"{order_data.get('amount_rub', 0):,.2f}".replace(",", " ")
    service_commission_str = f"{order_data.get('service_commission_rub', 0):,.2f}".replace(",", " ")
    network_fee_str = f"{order_data.get('network_fee_rub', 0):,.2f}".replace(",", " ")
    total_amount_str = f"{order_data.get('total_amount', 0):,.2f}".replace(",", " ")

    # Определяем заголовок для реквизитов пользователя
    user_details_title = "Реквизиты для получения RUB:" if order_data.get('action') == 'sell' else f"Адрес кошелька {crypto}:"

    # Экранируем данные от пользователя
    safe_username = html.escape(username or "N/A")
    safe_user_input = html.escape(user_input or "N/A")

    # Формируем список с деталями заявки
    details = [
        f"👤 <b>Пользователь:</b> {safe_username} (<code>{user_id}</code>)",
        f"\n<b>Детали заявки:</b>",
        f"  - <b>Тип:</b> {action} {crypto}",
        f"  - <b>Сумма в крипте:</b> <code>{amount_crypto_str} {crypto}</code>",
        f"  - <b>Эквивалент в RUB (чистыми):</b> <code>{amount_rub_str} RUB</code>",
        f"\n<b>Комиссии:</b>",
        f"  - <b>Сервис:</b> <code>{service_commission_str} RUB</code>",
        f"  - <b>Сеть:</b> <code>{network_fee_str} RUB</code>",
        f"\n<b>Итоговая сумма:</b> <code>{total_amount_str} RUB</code>",
        f"\n<b>{html.escape(user_details_title)}</b>",
        f"<code>{safe_user_input}</code>"
    ]

    # Если был применён промокод, добавляем заметную плашку в начало
    if order_data.get('promo_applied'):
        details.insert(1, "✅ <b>ИСПОЛЬЗОВАН ПРОМОКОД</b>")

    # Собираем финальный текст
    details_str = "\n".join(details)

    admin_text = (
        f"🔔 <b>Детали заявки #{order_number}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{details_str}\n\n"
    )

    # Клавиатура
    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_order_{order_id}_{user_id}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data=f"reject_order_{order_id}_{user_id}")
            ]
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

def get_final_confirmation_text_with_topic(order_number: int) -> str:
    """Финальное подтверждение для пользователя с информацией о тикете."""
    return (
        f"✅ *Ваша заявка #{order_number} успешно создана!*\n\n"
        f"Оператор уже получил уведомление и скоро свяжется с вами прямо в теме с вашей заявкой.\n\n"
        f"Всю дальнейшую переписку, пожалуйста, ведите в этой теме."
    )



def get_active_order_notice_text(order_number: int) -> str:
    """
    Возвращает текст-уведомление о том, что у пользователя уже есть активная заявка.
    """
    return (
        f"<b>❗️ Внимание</b>\n\n"
        f"У вас уже есть активная заявка <b>#{order_number}</b>. "
        f"Вы не можете создать новую, пока текущая не будет завершена.\n\n"
        f"Ниже представлена информация о вашей активной заявке:"
    )


def get_requisites_and_chat_prompt_text(action: str, crypto: str, total_amount: float, sbp_phone: str, sbp_bank: str, wallet_address: str) -> str:
    """
    Генерирует финальное сообщение с реквизитами и инструкцией для пользователя.
    """
    if action == 'buy':
        # Пользователь покупает крипту, мы даем ему реквизиты для оплаты в рублях
        payment_details = (
            f"Для завершения обмена, пожалуйста, переведите <b>{total_amount:.2f} RUB</b> по следующим реквизитам:\n\n"
            f"📞 Телефон (СБП): <code>{sbp_phone}</code>\n"
            f"🏦 Банк получателя: <b>{sbp_bank}</b>"
        )
        instruction = "После перевода, пожалуйста, отправьте <b>скриншот или чек об оплате</b> в этот чат."
    
    else: # sell
        # Пользователь продает крипту, мы даем ему наш криптокошелек
        payment_details = (
            f"Для завершения обмена, пожалуйста, переведите криптовалюту на наш кошелек:\n\n"
            f"<b>{crypto.upper()} Адрес:</b>\n<code>{wallet_address}</code>"
        )
        instruction = "После перевода, пожалуйста, отправьте <b>ID или хэш транзакции</b>, а также <b>ваши реквизиты для получения рублей</b> (номер карты/СБП и банк) в этот чат."

    return (
        f"✅ <b>Заявка создана!</b>\n\n"
        f"{payment_details}\n\n"
        f"‼️ <b>Важно:</b> {instruction}\n\n"
        f"Оператор скоро подключится к диалогу."
    )

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Возвращает простую клавиатуру с кнопкой "Отмена"."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel_transaction")]
    ])