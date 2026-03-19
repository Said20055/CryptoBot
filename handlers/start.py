# handlers/start.py
"""
Хендлеры: /start, главное меню, /profile, профиль.
"""

from aiogram import F, Router
from aiogram.exceptions import AiogramError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from config import ADMIN_CHAT_ID, MIN_WITHDRAWAL_AMOUNT, REFERRAL_PERCENTAGE
from utils import keyboards, texts
from utils.logging_config import logger
from utils.texts import WELCOME_PHOTO_URL, WELCOME_TEXT
from utils.database.db_helpers import acquire, transaction
from utils.database.db_queries import (
    get_user_profile, get_user_referral_info, save_or_update_user,
)

router = Router()


async def show_main_menu(event: Message | CallbackQuery):
    """Показывает главное меню (используется из нескольких хендлеров)."""
    msg = event.message if isinstance(event, CallbackQuery) else event
    try:
        await msg.answer_photo(
            photo=WELCOME_PHOTO_URL,
            caption=WELCOME_TEXT,
            reply_markup=keyboards.get_main_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        await msg.answer(
            text=WELCOME_TEXT,
            reply_markup=keyboards.get_main_keyboard(),
            parse_mode="HTML",
        )


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username or "Нет username"
    full_name = message.from_user.full_name

    referrer_id = None
    parts = message.text.split()
    if len(parts) > 1 and parts[1].startswith("ref"):
        try:
            referrer_id = int(parts[1][3:])
            if referrer_id == user_id:
                referrer_id = None
        except (ValueError, IndexError):
            logger.warning(f"Invalid referrer payload from user {user_id}: {parts[1]}")

    try:
        async with transaction() as conn:
            is_new_user = await save_or_update_user(conn, user_id, username, full_name, referrer_id)
    except Exception as e:
        logger.error(f"DB error in start_handler for user {user_id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.")
        return

    if is_new_user:
        for admin_id in ADMIN_CHAT_ID:
            try:
                await message.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"Новый пользователь: @{message.from_user.username or 'NoUsername'}\n"
                        f"Имя: {full_name}\nID: {user_id}"
                    ),
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id} about new user: {e}")

    await show_main_menu(message)


@router.callback_query(F.data.in_({"back_to_main_menu", "main_menu"}))
async def back_to_main_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except AiogramError:
        pass
    await show_main_menu(callback)
    await callback.answer()


@router.message(Command("profile"))
@router.callback_query(F.data == "profile")
async def profile_handler(event: Message | CallbackQuery):
    user_id = event.from_user.id
    msg = event.message if isinstance(event, CallbackQuery) else event
    bot_username = (await msg.bot.get_me()).username

    try:
        async with acquire() as conn:
            profile_data = await get_user_profile(conn, user_id)
            ref_info = await get_user_referral_info(conn, user_id)
    except Exception as e:
        logger.error(f"DB error in profile_handler for user {user_id}: {e}", exc_info=True)
        if isinstance(event, CallbackQuery):
            await event.answer("Ошибка загрузки данных", show_alert=True)
        else:
            await msg.answer("Произошла ошибка при загрузке ваших данных. Попробуйте позже.")
        return

    text, balance = texts.get_profile_text(
        user_id=user_id, bot_username=bot_username,
        profile_data=profile_data, ref_info=ref_info, ref_percentage=REFERRAL_PERCENTAGE,
    )
    keyboard = keyboards.get_profile_keyboard(balance, MIN_WITHDRAWAL_AMOUNT)

    if isinstance(event, CallbackQuery):
        try:
            await msg.delete()
        except AiogramError:
            pass
        await msg.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await event.answer()
    else:
        await msg.answer(text, reply_markup=keyboard, parse_mode="HTML")
