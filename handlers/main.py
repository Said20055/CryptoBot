"""
Основные хендлеры для главного меню и старта
"""
import aiosqlite
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import AiogramError
from config import ADMIN_CHAT_ID
from utils.logging_config import logger
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import activate_promo_for_user, get_user_profile, save_or_update_user
from utils.texts import WELCOME_PHOTO_URL, WELCOME_TEXT, HELP_TEXT, format_user_display_name, get_main_keyboard, get_back_to_main_menu_keyboard
from utils.states import UserPromoStates
from typing import Union

async def start_handler(event: Union[Message, CallbackQuery]):
    """
    Обработчик команды /start и возврата в главное меню (ФИНАЛЬНАЯ ВЕРСИЯ).
    """
    user_id = event.from_user.id
    username = event.from_user.username or "Нет username"
    full_name = event.from_user.full_name

    # --- НОВЫЙ ПАТТЕРН РАБОТЫ С БД ---
    is_new_user = False # Задаем значение по умолчанию
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # Передаем курсор как первый аргумент
                is_new_user = await save_or_update_user(cursor, user_id, username, full_name)
                await db.commit()
    except Exception as e:
        logger.error(f"DB error in start_handler for user {user_id}: {e}", exc_info=True)
        # Если БД упала, нужно как-то ответить пользователю
        error_message = "Произошла ошибка базы данных. Попробуйте позже."
        if isinstance(event, Message):
            await event.answer(error_message)
        else:
            await event.message.answer(error_message)
        return
    # --- КОНЕЦ НОВОГО ПАТТЕРНА ---

    logger.info(f"User {user_id} ({username}) {'saved as new' if is_new_user else 'updated'} in DB")
    
    # Отправляем уведомление админам
    if is_new_user:
        for admin_id in ADMIN_CHAT_ID:
            try:
                await event.bot.send_message(
                        chat_id=admin_id,
                        text=f"Пользователь запустил /start:\nUsername: {format_user_display_name(username)}\nПолное имя: {full_name}\nID: {user_id}\nНовый: {is_new_user}",
                        parse_mode=None
                )
                logger.info(f"Notification sent to admin {admin_id} about user {username}")
            except (ConnectionError, TimeoutError) as e:
                    logger.error(f"Failed to notify admin {admin_id} about user {user_id}: {e}")

    # Отправляем ответ пользователю
    if isinstance(event, Message):
        await event.answer_photo(
            photo= WELCOME_PHOTO_URL, 
            caption= WELCOME_TEXT, 
            reply_markup= get_main_keyboard(), 
            parse_mode="Markdown"
        )
    else: # CallbackQuery
        await event.message.answer_photo(
            photo= WELCOME_PHOTO_URL, 
            caption= WELCOME_TEXT, 
            reply_markup= get_main_keyboard(), 
            parse_mode="Markdown"
        )
        try:
            await event.message.delete()
        except AiogramError as e:
            logger.warning(f"Could not delete message: {e}")

async def help_handler(message: Message):
    """Обработчик команды /help"""
    await message.answer(HELP_TEXT, parse_mode="Markdown")

async def id_handler(message: Message):
    """Обработчик команды /id"""
    user_id = message.from_user.id
    await message.answer(f"Ваш Telegram ID: {user_id}")
    logger.info(f"User {user_id} requested their Telegram ID")

async def handle_photo(message: Message):
    # photo — это список размеров, берём последний (самый большой)
    file_id = message.photo[-1].file_id
    await message.answer(f"file_id фото: {file_id}")

async def image_handler(message: Message):
    """Обработчик изображений"""
    if message.photo:
        photo_id = message.photo[-1].file_id
        username = message.from_user.username or message.from_user.full_name or "Пользователь"
        user_id = message.from_user.id
        await handle_photo(message)
        logger.info(f"Received photo with ID: {photo_id} from user {user_id}")
        
        # Подтверждаем пользователю
        await message.answer("✅ Изображение получено и отправлено оператору.")
        
        # Отправляем изображение админам
        from utils.texts import format_user_display_name
        admin_text = (
            f"📷 *Изображение от пользователя:* {format_user_display_name(username)} (ID: {user_id})\n\n"
            f"Пользователь отправил изображение. Ответьте ему, используя кнопку ниже."
        )
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        admin_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💬 Ответить пользователю", callback_data=f"admin_reply_{user_id}")]
            ]
        )
        
        for admin_id in ADMIN_CHAT_ID:
            try:
                await message.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_id,
                    caption=admin_text,
                    reply_markup=admin_keyboard,
                    parse_mode="Markdown"
                )
                logger.info(f"Photo sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send photo to admin {admin_id}: {e}")
async def profile_handler(event: Union[Message, CallbackQuery]):
    """
    Универсальный обработчик для команды /profile и кнопки "Профиль" (ФИНАЛЬНАЯ ВЕРСИЯ).
    """
    user_id = event.from_user.id
    profile_data = None
    
    # --- НОВЫЙ ПАТТЕРН РАБОТЫ С БД ---
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # Передаем курсор как первый аргумент
                profile_data = await get_user_profile(cursor, user_id)
    except Exception as e:
        logger.error(f"DB error in profile_handler for user {user_id}: {e}", exc_info=True)
        text = "Произошла ошибка базы данных. Попробуйте позже."
        if isinstance(event, Message):
            await event.answer(text)
        else:
            await event.message.answer(text)
        return
    # --- КОНЕЦ НОВОГО ПАТТЕРНА ---

    keyboard = get_back_to_main_menu_keyboard()
    
    if profile_data:
        username = profile_data['username'] or "не указан"
        # Считаем только успешные обмены, как и хотели
        text = (
            f"<b>👤 Ваш профиль</b>\n\n"
            f"<b>ID:</b> <code>{user_id}</code>\n"
            f"<b>Никнейм:</b> @{username}\n\n"
            f"<b>📊 Статистика успешных обменов:</b>\n"
            f"  - <b>Всего завершено:</b> {profile_data['total_orders']}\n"
            f"  - <b>Общий объем:</b> {profile_data['total_volume_rub']:.2f} RUB"
        )
    else:
        text = "Не удалось найти ваш профиль. Возможно, у вас еще не было успешных обменов."

    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")
    elif isinstance(event, CallbackQuery):
        await event.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        try:
            await event.message.delete()
        except Exception as e:
            logger.warning(f"Could not delete message: {e}")
            
async def process_user_promo_code(message: Message, state: FSMContext):
    """Проверяет и активирует промокод пользователя (ИСПРАВЛЕННАЯ ВЕРСИЯ)."""
    code = message.text.strip()
    
    # --- НОВЫЙ ПАТТЕРН РАБОТЫ С БД ---
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # Передаем курсор как первый аргумент
                result = await activate_promo_for_user(cursor, message.from_user.id, code)
                await db.commit() # Фиксируем активацию
    except Exception as e:
        logger.error(f"DB error during promo activation for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.")
        await state.clear()
        return
    # --- КОНЕЦ НОВОГО ПАТТЕРНА ---

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

async def promo_command_handler(event: Union[Message, CallbackQuery], state: FSMContext):
    """
    Универсальный обработчик для команды /promo и кнопки "Активировать промокод".
    """
    # Текст и установка состояния одинаковы для обоих случаев
    text = "Введите ваш промокод:"
    await state.set_state(UserPromoStates.waiting_for_code)

    # Определяем, как был вызван хендлер, и отвечаем соответствующим образом
    if isinstance(event, Message):
        # Если это команда /promo, просто отправляем ответ
        await event.answer(text)
    elif isinstance(event, CallbackQuery):
        # Если это кнопка, отправляем новое сообщение и отвечаем на колбек
        await event.message.answer(text)
        await event.answer() # Это убирает "часики" на кнопке
