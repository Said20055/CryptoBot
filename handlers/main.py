# handlers/main.py (ВЕРСИЯ С ДЕКОРАТОРАМИ)

"""
Основные хендлеры для главного меню, профиля и промокодов.
"""
import aiosqlite
from typing import Union
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import AiogramError

# Импортируем наш роутер
from handlers.router import main_router as router

from config import ADMIN_CHAT_ID
from utils.logging_config import logger
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import activate_promo_for_user, get_user_profile, save_or_update_user
from utils.texts import WELCOME_PHOTO_URL, WELCOME_TEXT, format_user_display_name, get_main_keyboard, get_back_to_main_menu_keyboard
from utils.states import UserPromoStates

# =============================================================================
# --- БЛОК: СТАРТ / ГЛАВНОЕ МЕНЮ ---
# =============================================================================

async def _show_main_menu(message: Message, is_new_user: bool):
    """Внутренняя функция для отправки главного меню."""
    if is_new_user:
        for admin_id in ADMIN_CHAT_ID:
            try:
                await message.bot.send_message(
                    chat_id=admin_id,
                    text=f"Новый пользователь: @{message.from_user.username or 'NoUsername'}\n"
                         f"Имя: {message.from_user.full_name}\nID: {message.from_user.id}",
                    parse_mode=None
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id} about new user: {e}")
    
    await message.answer_photo(
        photo=WELCOME_PHOTO_URL,
        caption=WELCOME_TEXT,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML" # Рекомендую перейти на HTML
    )

@router.message(Command(commands=['start']))
async def start_command_handler(message: Message):
    """Обработчик команды /start."""
    user_id = message.from_user.id
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                is_new_user = await save_or_update_user(cursor, user_id, message.from_user.username, message.from_user.full_name)
                await db.commit()
    except Exception as e:
        logger.error(f"DB error in start_handler for user {user_id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.")
        return
    
    await _show_main_menu(message, is_new_user)

@router.callback_query(F.data == 'back_to_main_menu')
async def back_to_main_menu_handler(callback_query: CallbackQuery):
    """Обработчик кнопки 'Назад в главное меню'."""
    # При возврате в меню нам не нужно снова сохранять пользователя
    await _show_main_menu(callback_query.message, is_new_user=False)
    try:
        await callback_query.message.delete()
    except AiogramError:
        pass
    await callback_query.answer()


# =============================================================================
# --- БЛОК: ПРОФИЛЬ ---
# =============================================================================

async def _get_profile_text(user_id: int) -> str:
    """Внутренняя функция для получения текста профиля."""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                profile_data = await get_user_profile(cursor, user_id)
    except Exception as e:
        logger.error(f"DB error in profile_handler for user {user_id}: {e}", exc_info=True)
        return "Произошла ошибка базы данных. Попробуйте позже."

    if profile_data:
        username = profile_data['username'] or "не указан"
        return (
            f"<b>👤 Ваш профиль</b>\n\n"
            f"<b>ID:</b> <code>{user_id}</code>\n"
            f"<b>Никнейм:</b> @{username}\n\n"
            f"<b>📊 Статистика успешных обменов:</b>\n"
            f"  - <b>Всего завершено:</b> {profile_data['total_orders']}\n"
            f"  - <b>Общий объем:</b> {profile_data['total_volume_rub']:.2f} RUB"
        )
    return "Не удалось найти ваш профиль. Возможно, у вас еще не было успешных обменов."

@router.message(Command(commands=['profile']))
async def profile_command_handler(message: Message):
    """Обработчик команды /profile."""
    text = await _get_profile_text(message.from_user.id)
    await message.answer(text, reply_markup=get_back_to_main_menu_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == 'profile')
async def profile_callback_handler(callback_query: CallbackQuery):
    """Обработчик кнопки 'Профиль'."""
    text = await _get_profile_text(callback_query.from_user.id)
    await callback_query.message.answer(text, reply_markup=get_back_to_main_menu_keyboard(), parse_mode="HTML")
    try:
        await callback_query.message.delete()
    except AiogramError:
        pass
    await callback_query.answer()


# =============================================================================
# --- БЛОК: ПРОМОКОДЫ ---
# =============================================================================

@router.message(Command(commands=['promo']))
@router.callback_query(F.data == 'activate_promo')
async def promo_command_handler(event: Union[Message, CallbackQuery], state: FSMContext):
    """Обработчик команды /promo и кнопки 'Активировать промокод'."""
    await state.set_state(UserPromoStates.waiting_for_code)
    text = "Введите ваш промокод:"
    
    if isinstance(event, Message):
        await event.answer(text)
    else: # CallbackQuery
        await event.message.answer(text)
        await event.answer()

@router.message(UserPromoStates.waiting_for_code)
async def process_user_promo_code(message: Message, state: FSMContext):
    """Ловит ввод промокода от пользователя."""
    code = message.text.strip()
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                result = await activate_promo_for_user(cursor, message.from_user.id, code)
                await db.commit()
    except Exception as e:
        logger.error(f"DB error during promo activation for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.")
        await state.clear()
        return

    if result == "success":
        await message.answer("✅ Промокод успешно активирован! Ваш следующий обмен будет без комиссии.")
    elif result == "invalid_or_expired":
        await message.answer("❌ Такого промокода не существует, он неактивен, или у него закончились использования.")
    elif result == "already_active":
        await message.answer("⚠️ У вас уже есть другой активный промокод. Сначала используйте его.")
    elif result == "already_redeemed":
        await message.answer("⚠️ Вы уже использовали этот промокод ранее.")
    else: # 'error'
        await message.answer("Произошла системная ошибка, попробуйте позже.")
    
    await state.clear()