from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .callbacks import CryptoInputSwitch, CryptoSelection, RubInputSwitch, OrdersPage, AdminOrderAction, CancelOrder


def get_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 Купить крипту", callback_data="buy"),
        InlineKeyboardButton(text="💸 Продать крипту", callback_data="sell"),
    )
    builder.row(
        InlineKeyboardButton(text="👨‍💼 Оператор", url="https://t.me/jenya2hh"),
        InlineKeyboardButton(text="👤 Профиль и Рефералка", callback_data="profile"),
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Промокод", callback_data="activate_promo"),
        InlineKeyboardButton(text="🎰 Лотерея", callback_data="lottery_menu"),
    )
    builder.row(InlineKeyboardButton(text="📋 Мои заказы", callback_data=OrdersPage(page=0).pack()))
    builder.row(InlineKeyboardButton(text="🌎 Подключиться к ExpressVPN", url="https://t.me/Express_vpn1_bot"))
    builder.row(InlineKeyboardButton(text="⭐ Отзывы", url="https://t.me/+obvt9s7jKgYzNzUy"))
    return builder.as_markup()


def get_back_to_main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ В главное меню", callback_data="back_to_main_menu")
    return builder.as_markup()


def get_crypto_selection_keyboard(action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🟡 Bitcoin (BTC)", callback_data=CryptoSelection(action=action, crypto="BTC").pack())
    builder.row(
        InlineKeyboardButton(text="🔷 TRON (TRX)", callback_data=CryptoSelection(action=action, crypto="TRX").pack()),
        InlineKeyboardButton(text="💵 Tether (USDT)", callback_data=CryptoSelection(action=action, crypto="USDT").pack()),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def get_crypto_details_keyboard(action: str, crypto: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Ввести сумму в ₽", callback_data=RubInputSwitch(action=action, crypto=crypto).pack())
    builder.button(text="⬅️ Отмена", callback_data="cancel_transaction")
    builder.adjust(1)
    return builder.as_markup()


def get_rub_input_keyboard(action: str, crypto: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"🔄 Ввести сумму в {crypto}",
        callback_data=CryptoInputSwitch(action=action, crypto=crypto).pack(),
    )
    builder.button(text="⬅️ Отмена", callback_data="cancel_transaction")
    builder.adjust(1)
    return builder.as_markup()


def get_final_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Все верно, получить реквизиты", callback_data="final_confirm_and_get_requisites")
    builder.button(text="❌ Отменить", callback_data="cancel_transaction")
    builder.adjust(1)
    return builder.as_markup()


def get_final_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📎 Загрузить чек", callback_data="upload_receipt")
    builder.button(text="❌ Отменить заявку", callback_data=CancelOrder(order_id=order_id).pack())
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Отмена", callback_data="cancel_transaction")
    return builder.as_markup()


def get_orders_pagination_keyboard(page: int, total: int, per_page: int = 5) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if page > 0:
        builder.button(text="‹ Назад", callback_data=OrdersPage(page=page - 1).pack())
    if (page + 1) * per_page < total:
        builder.button(text="Вперёд ›", callback_data=OrdersPage(page=page + 1).pack())
    builder.button(text="⬅️ В главное меню", callback_data="back_to_main_menu")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_profile_keyboard(balance: float, min_withdrawal: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📈 Мои начисления", callback_data="ref_earnings_history")
    if balance >= min_withdrawal:
        builder.button(text=f"💸 Вывести {balance:,.2f} RUB", callback_data="ref_withdraw")
    builder.button(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_persistent_reply_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Завершить переписку", callback_data="end_reply_session")
    return builder.as_markup()


# --- Admin keyboards ---

def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="📢 Сделать рассылку", callback_data="admin_broadcast")
    builder.button(text="🎁 Создать промокод", callback_data="admin_create_promo")
    builder.button(text="⚙️ Управление реквизитами", callback_data="admin_settings")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_order_keyboard(order_id: int, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Подтвердить",
        callback_data=AdminOrderAction(action="confirm", order_id=order_id, user_id=user_id).pack(),
    )
    builder.button(
        text="❌ Отменить",
        callback_data=AdminOrderAction(action="reject", order_id=order_id, user_id=user_id).pack(),
    )
    return builder.as_markup()


def back_to_admin_panel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад в админ-панель", callback_data="back_to_admin_panel")
    return builder.as_markup()


def get_broadcast_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить всем", callback_data="confirm_broadcast")
    builder.button(text="❌ Отмена", callback_data="cancel_broadcast")
    builder.adjust(1)
    return builder.as_markup()


def get_promo_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="% от комиссии", callback_data="promo_type_percent")
    builder.button(text="Фиксированная сумма (RUB)", callback_data="promo_type_fixed")
    builder.button(text="❌ Отмена", callback_data="back_to_admin_panel")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_lottery_menu_keyboard(can_play: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_play:
        builder.button(text="🎲 Испытать удачу!", callback_data="lottery_play")
    builder.button(text="⬅️ Назад в главное меню", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()
