from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional

from .callbacks import CryptoInputSwitch, CryptoSelection, RubInputSwitch


def get_main_keyboard() -> InlineKeyboardMarkup:
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

def get_broadcast_confirmation_keyboard():
    """Создает клавиатуру для подтверждения рассылки."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить всем", callback_data="confirm_broadcast")
    builder.button(text="❌ Отмена", callback_data="cancel_broadcast")
    builder.adjust(1)
    return builder.as_markup()

def get_back_to_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="main_menu")]
        ]
    )


def get_crypto_selection_keyboard(action: str) -> InlineKeyboardMarkup:
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


def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Сделать рассылку", callback_data="admin_broadcast")
    builder.button(text="🎁 Создать промокод", callback_data="admin_create_promo")
    builder.button(text="⚙️ Управление реквизитами", callback_data="admin_settings")
    builder.adjust(1)
    return builder.as_markup()


def get_persistent_reply_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Завершить переписку", callback_data="end_reply_session")]
    ])


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel_transaction")]
    ])
