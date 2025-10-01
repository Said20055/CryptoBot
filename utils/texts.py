import html

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Tuple





# --- Константы для главного меню ---
WELCOME_PHOTO_URL = "AgACAgIAAxkBAAOCaMe8_YoQvR8VmQgxGrvwJ2Ew8bQAAqP4MRvD4zhKhf8sL6uWlyABAAMCAAN5AAM2BA"

WELCOME_TEXT = (
    "👋 <b>Добро пожаловать в ExpressObmen P2P!</b>\n\n"
    "💸 <b>Обмен криптовалюты без лишних комиссий и задержек!</b>\n"
    "⚡️ <b>Самые низкие комиссии на рынке</b> — мы заботимся о вашем бюджете!\n"
    "🔒 <b>Безопасные транзакции</b> и гарантия надежности.\n"
    "🚀 <b>Моментальные обмены 24/7</b> в пару кликов.\n"
    "📱 <b>Удобный интерфейс прямо в Telegram</b> — просто выберите валюту и сумму!\n\n"
    "<b>Начните обмен прямо сейчас</b> и ощутите скорость и выгоду с <b>ExpressObmen P2P!</b>\n\n"
)

HELP_TEXT = "памагите"

# --- Функции для генерации клавиатур ---



# --- Функции для генерации текстов сообщений ---

SELL_CRYPTO_TEXT = "<b>🧾 Меню продажи</b>\n\nВыберите криптовалюту для продажи и следуйте подсказкам."
BUY_CRYPTO_TEXT = "<b>🧾 Меню покупки</b>\n\nВыберите криптовалюту для покупки и следуйте подсказкам."
OPERATOR_CONTACT_TEXT = "👨‍💼 <b>Связь с оператором:</b> @jenya2hh\n\nНапишите оператору для получения помощи с обменом."
SEND_TX_LINK_PROMPT = "📎 <b>Отправьте ссылку на транзакцию в блокчейне.</b>\n\nПосле отправки оператор проверит ее и обработает заявку."
REPLY_TO_OPERATOR_PROMPT = "💬 <b>Отправьте ваше сообщение для оператора:</b>"


def format_user_display_name(username: str) -> str:
    """Форматирует имя пользователя для отображения."""
    if not username or username in ["Пользователь", "Нет username"]:
        return "Пользователь"
    
    if ' ' not in username and not username.startswith('@'):
        return f"@{username}"
    
    return username

def get_crypto_prompt_text(action: str, crypto: str, rate: float) -> str:
    """Возвращает универсальный текст с предложением ввести сумму в криптовалюте."""
    if action == 'sell':
        action_text = f"<b>Продажа {html.escape(crypto)}</b>"
        prompt_text = f"Пожалуйста, введите сумму в <b>{html.escape(crypto)}</b>, которую вы хотите продать."
    else:
        action_text = f"<b>Покупка {html.escape(crypto)}</b>"
        prompt_text = f"Пожалуйста, введите сумму в <b>{html.escape(crypto)}</b>, которую вы хотите купить."

    formatted_rate = f"{rate:,.2f}".replace(",", " ")
    return (
        f"{action_text}\n\n"
        f"Текущий курс: <code>1 {crypto} ≈ {formatted_rate} RUB</code>\n\n"
        f"{prompt_text}"
    )

def get_rub_prompt_text(action: str, crypto: str, rate: float) -> str:
    """Возвращает универсальный текст с предложением ввести сумму в рублях."""
    if action == 'sell':
        action_text = f"<b>Продажа {html.escape(crypto)}</b>"
        prompt_text = f"Пожалуйста, введите сумму в <b>RUB</b>, на которую вы хотите продать <b>{html.escape(crypto)}</b>."
    else:
        action_text = f"<b>Покупка {html.escape(crypto)}</b>"
        prompt_text = f"Пожалуйста, введите сумму в <b>RUB</b>, на которую вы хотите купить <b>{html.escape(crypto)}</b>."

    formatted_rate = f"{rate:,.2f}".replace(",", " ")
    return (
        f"{action_text}\n\n"
        f"Текущий курс: <code>1 {crypto} ≈ {formatted_rate} RUB</code>\n\n"
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



def get_final_confirmation_text_with_topic(order_number: int) -> str:
    """Финальное подтверждение для пользователя с информацией о тикете."""
    return (
        f"✅ <b>Ваша заявка #{order_number} успешно создана!</b>\n\n"
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


def get_requisites_and_chat_prompt_text(
    action: str,
    crypto: str,
    total_amount: float,
    sbp_phone: str,
    sbp_bank: str,
    wallet_address: str
) -> str:
    """
    Генерирует финальное сообщение с реквизитами и инструкцией для пользователя.
    Содержит уведомление о начале диалога с оператором.
    """
    if action == 'buy':
        # Пользователь покупает криптовалюту → переводит рубли
        payment_details = (
            f"💰 Переведите <b>{total_amount:.2f} RUB</b> по следующим реквизитам:\n\n"
            f"📞 Телефон (СБП): <code>{sbp_phone}</code>\n"
            f"🏦 Банк получателя: <b>{sbp_bank}</b>"
        )
        instruction = "После перевода отправьте <b>скриншот или чек об оплате</b> прямо в этот чат."

    else:  # sell
        # Пользователь продает криптовалюту → переводит на кошелек
        payment_details = (
            f"💰 Переведите криптовалюту на наш кошелек:\n\n"
            f"<b>{crypto.upper()} Адрес:</b>\n<code>{wallet_address}</code>"
        )
        instruction = (
            "После перевода отправьте <b>ID или хэш транзакции</b>, а также "
            "<b>ваши реквизиты для получения рублей</b> (номер карты/СБП и банк)."
        )

    return (
        f"✅ <b>Заявка создана!</b>\n\n"
        f"{payment_details}\n\n"
        f"⚠️ <b>Важно:</b> {instruction}\n\n"
        f"👨‍💼 <b>Начат диалог с оператором.</b>\n"
        f"✉️ Все ваши сообщения из этого чата автоматически пересылаются оператору, "
        f"и его ответы будут приходить сюда."
    )

