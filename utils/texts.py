"""
Все пользовательские тексты сообщений (Russian).
Только текст — клавиатуры живут в keyboards.py.
"""

from datetime import datetime, timedelta
import html
from typing import List, Tuple

from .helpers import format_timedelta


# --- Главное меню ---

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

SELL_CRYPTO_TEXT = "<b>💳 Меню продажи</b>\n\nВыберите криптовалюту для продажи и следуйте подсказкам."
BUY_CRYPTO_TEXT = "<b>💳 Меню покупки</b>\n\nВыберите криптовалюту для покупки и следуйте подсказкам."
REPLY_TO_OPERATOR_PROMPT = "💬 <b>Отправьте ваше сообщение для оператора:</b>"


# --- Лотерея ---

def get_lottery_menu_text(lottery_info: dict, can_get_ticket: bool) -> str:
    header = "🎰 <b>Лотерея ExpressObmen P2P</b>\n\n"
    if can_get_ticket:
        ticket_text = "✨ У вас есть <b>1</b> бесплатная игра! Готовы испытать удачу?"
    else:
        next_ticket_time = lottery_info.get('last_ticket') + timedelta(hours=24)
        time_left = next_ticket_time - datetime.now()
        formatted_time = format_timedelta(time_left)
        ticket_text = f"⏳ Следующая бесплатная игра будет доступна через: <b>{formatted_time}</b>"
    return f"{header}{ticket_text}"


def get_lottery_win_text(amount: float) -> str:
    return (
        f"🎉 <b>Поздравляем!</b> 🎉\n\n"
        f"Вы выиграли <b>{amount:,.2f} RUB</b>!\n\n"
        f"Средства зачислены на ваш реферальный баланс. Вы можете проверить его в разделе "
        f"«💎 Реферальная программа»."
    )


# --- Профиль и реферальная программа ---

def format_user_display_name(username: str) -> str:
    if not username or username in ["Пользователь", "Нет username"]:
        return "Пользователь"
    if ' ' not in username and not username.startswith('@'):
        return f"@{username}"
    return username


def get_profile_text(user_id: int, profile_data: dict, bot_username: str,
                     ref_info: dict, ref_percentage: float) -> tuple:
    """Возвращает (текст профиля, баланс) для get_profile_keyboard."""
    if profile_data:
        username = profile_data['username'] or "не указан"
        profile_block = (
            "<b>👤 Ваш профиль</b>\n\n"
            f"<b>ID:</b> <code>{user_id}</code>\n"
            f"<b>Никнейм:</b> @{username}\n\n"
            "<b>📊 Статистика успешных обменов:</b>\n"
            f"  • <b>Всего завершено:</b> {profile_data['total_orders']}\n"
            f"  • <b>Общий объём:</b> {profile_data['total_volume_rub']:.2f} RUB"
        )
    else:
        profile_block = (
            "<b>👤 Ваш профиль</b>\n\n"
            "Не удалось найти ваши данные. Возможно, у вас ещё не было успешных обменов."
        )

    referral_link = f"https://t.me/{bot_username}?start=ref{user_id}"
    balance = ref_info.get('balance', 0.0)
    referral_count = ref_info.get('referral_count', 0)

    referral_block = (
        "\n\n<b>👥 Ваша реферальная программа</b>\n\n"
        f"Приглашайте друзей и получайте <b>{ref_percentage:.1f}%</b> "
        "с суммы каждого их успешного обмена!\n\n"
        "🔗 <b>Ваша уникальная ссылка:</b>\n"
        f"<code>{referral_link}</code>\n"
        "<i>(Нажмите, чтобы скопировать)</i>\n\n"
        "📈 <b>Реферальная статистика:</b>\n"
        f"  • Приглашено пользователей: <b>{referral_count}</b>\n"
        f"  • Текущий баланс: <b>{balance:,.2f} RUB</b>\n\n"
        "Накопленные средства можно вывести, когда баланс достигнет минимальной суммы — 300 рублей."
    )

    return profile_block + referral_block, balance


def get_referral_earnings_text(earnings: list, balance: float) -> str:
    if not earnings:
        return (
            "📈 <b>История начислений</b>\n\n"
            "У вас пока нет реферальных начислений.\n\n"
            "Приглашайте друзей по вашей ссылке, и после каждого их успешного обмена "
            "вы будете получать вознаграждение!"
        )

    header = (
        f"📈 <b>История последних начислений</b>\n"
        f"💰 Ваш текущий баланс: <b>{balance:,.2f} RUB</b>\n\n"
    )
    lines = []
    for record in earnings:
        amount = record['amount']
        created_at = record['created_at']  # asyncpg возвращает datetime-объект
        formatted_date = created_at.strftime('%d.%m.%Y %H:%M')
        lines.append(f"<code>+{amount:,.2f} RUB</code>   <i>{formatted_date}</i>")
    return header + "\n".join(lines)


# --- Торговый flow ---

def get_crypto_prompt_text(action: str, crypto: str, rate: float) -> str:
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


def get_user_requisites_prompt_text(action: str, crypto: str) -> str:
    if action == 'buy':
        return (
            f"✅ <b>Отлично!</b>\n\n"
            f"Теперь, пожалуйста, отправьте <b>адрес вашего {crypto.upper()} кошелька</b>, "
            f"на который мы отправим криптовалюту после получения вашей оплаты."
        )
    return (
        "✅ <b>Отлично!</b>\n\n"
        "Теперь, пожалуйста, отправьте сообщение с вашими реквизитами для получения оплаты. "
        "Например:\n"
        "<code>Иванов Иван Иванович, Сбербанк, 89991234567</code>"
    )


def get_transaction_summary_text(
    action: str, crypto: str, amount_crypto: float, amount_rub: float,
    total_amount: float, base_service_rub: float, base_network_rub: float,
    promo_applied: bool, promo_discount_rub: float, user_requisites: str,
) -> str:
    if action == 'buy':
        requisites_title = "Ваш кошелек для получения"
        total_line = f"<b>К оплате:</b> <code>{total_amount:.0f} RUB</code>"
    else:
        requisites_title = "Ваши реквизиты для получения"
        total_line = f"<b>К получению:</b> <code>{total_amount:.0f} RUB</code>"

    discount_line = f"<b>Скидка по промокоду:</b> <code>-{promo_discount_rub:.0f} RUB</code>\n" if promo_applied else ""

    return (
        f"<b>🔍 Пожалуйста, проверьте все данные:</b>\n\n"
        f"<b>Действие:</b> {'Покупка' if action == 'buy' else 'Продажа'} {crypto.upper()}\n"
        f"<b>Сумма в криптовалюте:</b> <code>{amount_crypto:.8f} {crypto.upper()}</code>\n"
        f"<b>Сумма в рублях:</b> <code>{amount_rub:.0f} RUB</code>\n\n"
        f"<b>{requisites_title}:</b>\n"
        f"<code>{html.escape(user_requisites)}</code>\n\n"
        f"<b>Комиссия сервиса:</b> {base_service_rub:.0f} RUB\n"
        f"<b>Комиссия сети:</b> {base_network_rub:.0f} RUB\n"
        f"{discount_line}\n"
        f"{total_line}\n\n"
        f"Если все верно, нажмите кнопку ниже."
    )


def get_admin_order_notification_text(
    order_id: int, order_number: int, user_id: int, username: str,
    order_data: dict, user_input: str,
) -> str:
    """Текст уведомления о новой заявке для темы поддержки."""
    action = order_data.get('action', 'N/A').title()
    crypto = order_data.get('crypto', 'N/A')

    amount_crypto_str = f"{order_data.get('amount_crypto', 0):,.8f}".rstrip('0').rstrip('.')
    amount_rub_str = f"{order_data.get('amount_rub', 0):,.0f}".replace(",", " ")
    service_commission_str = f"{order_data.get('service_commission_rub', 0):,.0f}".replace(",", " ")
    network_fee_str = f"{order_data.get('network_fee_rub', 0):,.0f}".replace(",", " ")
    total_amount_str = f"{int(order_data.get('total_amount', 0)):.0f}".replace(",", " ")

    user_details_title = (
        "Реквизиты для получения RUB:"
        if order_data.get('action') == 'sell'
        else f"Адрес кошелька {crypto}:"
    )

    details = [
        f"👤 <b>Пользователь:</b> {html.escape(username or 'N/A')} (<code>{user_id}</code>)",
        "\n<b>Детали заявки:</b>",
        f"  - <b>Тип:</b> {action} {crypto}",
        f"  - <b>Сумма в крипте:</b> <code>{amount_crypto_str} {crypto}</code>",
        f"  - <b>Эквивалент в RUB (чистыми):</b> <code>{amount_rub_str} RUB</code>",
        "\n<b>Комиссии:</b>",
        f"  - <b>Сервис:</b> <code>{service_commission_str} RUB</code>",
        f"  - <b>Сеть:</b> <code>{network_fee_str} RUB</code>",
        f"\n<b>Итоговая сумма:</b> <code>{total_amount_str} RUB</code>",
        f"\n<b>{html.escape(user_details_title)}</b>",
        f"<code>{html.escape(user_input or 'N/A')}</code>",
    ]

    if order_data.get('promo_applied'):
        details.insert(1, "✅ <b>ИСПОЛЬЗОВАН ПРОМОКОД</b>")

    return (
        f"🔔 <b>Детали заявки #{order_number}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{chr(10).join(details)}\n\n"
    )


def get_requisites_and_chat_prompt_text(
    action: str, crypto: str, total_amount: float,
    sbp_phone: str, sbp_bank: str, wallet_address: str,
) -> str:
    if action == 'buy':
        payment_details = (
            f"💰 Переведите <b>{total_amount:.0f} RUB</b> по следующим реквизитам:\n\n"
            f"📞 Телефон (СБП): <code>{sbp_phone}</code>\n"
            f"🏦 Банк получателя: <b>{sbp_bank}</b>"
        )
        instruction = "После перевода отправьте <b>скриншот или чек об оплате</b> прямо в этот чат."
    else:
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


def get_active_order_notice_text(order_number: int) -> str:
    return (
        f"<b>❗️ Внимание</b>\n\n"
        f"У вас уже есть активная заявка <b>#{order_number}</b>. "
        f"Вы не можете создать новую, пока текущая не будет завершена.\n\n"
        f"Ниже представлена информация о вашей активной заявке:"
    )


# --- Вывод реферального баланса ---

def get_withdrawal_prompt_text(min_amount: int, balance: float) -> str:
    return (
        "💰 <b>Вывод реферального баланса</b>\n\n"
        f"Ваш баланс: <b>{balance:,.2f} RUB</b>.\n"
        f"Минимальная сумма для вывода: <b>{min_amount} RUB</b>.\n\n"
        "Пожалуйста, отправьте в следующем сообщении реквизиты для получения средств "
        "(например, номер карты и название банка).\n\n"
        "<b>Пример:</b> <code>5555 4444 3333 2222, Сбербанк</code>"
    )


def get_withdrawal_request_admin_notification(user_id: int, username: str, amount: float) -> str:
    return (
        "💸 <b>Заявка на вывод реферальных средств</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Пользователь:</b> {format_user_display_name(username)} (<code>{user_id}</code>)\n"
        f"💰 <b>Сумма:</b> <code>{amount:,.2f} RUB</code>\n\n"
        "Пожалуйста, свяжитесь с пользователем для уточнения реквизитов и обработки выплаты."
    )


# --- Статистика ---

def get_statistics_text(stats: dict) -> str:
    return (
        "<b>📊 Статистика бота</b>\n\n"
        "<b>👤 Новые пользователи:</b>\n"
        f"  — За 24 часа: <i>{stats.get('users_day', 0)}</i>\n"
        f"  — За 7 дней: <i>{stats.get('users_week', 0)}</i>\n"
        f"  — За 30 дней: <i>{stats.get('users_month', 0)}</i>\n\n"
        "<b>Активность в лотерее:</b>\n"
        f"  — Сыграно в 🎰 за 24 часа: <i>{stats.get('lottery_day', 0)}</i>"
    )
