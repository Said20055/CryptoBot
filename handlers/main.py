"""
Основные хендлеры для главного меню и старта
"""

from aiogram.types import Message, CallbackQuery
from config import ADMIN_CHAT_ID
from utils.logging_config import logger
from utils.database import get_user_profile, save_or_update_user
from utils.texts import WELCOME_TEXT, HELP_TEXT, get_main_keyboard, get_back_to_main_keyboard
from typing import Union

async def start_handler(event: Message | CallbackQuery):
    """Обработчик команды /start"""
    photo_url = "https://postimg.cc/LhjTfzJd"
    keyboard = get_main_keyboard()
    
    if isinstance(event, Message):
        username = event.from_user.username or "Нет username"
        full_name = event.from_user.full_name
        user_id = event.from_user.id
        is_new_user = await save_or_update_user(user_id, username, full_name)
        logger.info(f"User {user_id} ({username}) {'saved as new' if is_new_user else 'updated'} in DB")
        
        # Отправляем уведомление админам при каждом /start
        for admin_id in ADMIN_CHAT_ID:
            try:
                await event.bot.send_message(
                    chat_id=admin_id,
                    text=f"Пользователь запустил /start:\nUsername: @{username}\nПолное имя: {full_name}\nID: {user_id}\nНовый: {is_new_user}",
                    parse_mode=None
                )
                logger.info(f"Notification sent to admin {admin_id} about user {username}")
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id} about user {user_id}: {e}")
        
        await event.answer_photo(
            photo=photo_url, caption=WELCOME_TEXT, reply_markup=keyboard, parse_mode="Markdown"
        )
    else:  # isinstance(event, CallbackQuery)
        logger.info(f"User {event.from_user.id} returned to main menu via callback")
        await event.message.answer_photo(
            photo=photo_url, caption=WELCOME_TEXT, reply_markup=keyboard, parse_mode="Markdown"
        )
        try:
            await event.message.delete()
        except Exception as e:
            logger.warning(f"Could not delete message: {e}")

async def help_handler(message: Message):
    """Обработчик команды /help"""
    await message.answer(HELP_TEXT, parse_mode="Markdown")

async def id_handler(message: Message):
    """Обработчик команды /id"""
    user_id = message.from_user.id
    await message.answer(f"Ваш Telegram ID: {user_id}")
    logger.info(f"User {user_id} requested their Telegram ID")

async def image_handler(message: Message):
    """Обработчик изображений"""
    if message.photo:
        photo_id = message.photo[-1].file_id
        username = message.from_user.username or message.from_user.full_name or "Пользователь"
        user_id = message.from_user.id
        
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
    Универсальный обработчик для команды /profile и кнопки "Профиль".
    Показывает статистику пользователя.
    """
    keyboard = get_back_to_main_keyboard()
    # Получаем user_id. Эта строка работает и для Message, и для CallbackQuery.
    user_id = event.from_user.id
    
    # Вызываем функцию для получения данных профиля из БД
    profile_data = await get_user_profile(user_id)
    
    if profile_data:
        # Если данные получены, форматируем красивый ответ
        username = profile_data['username'] or "не указан"

        text = (
            f"<b>👤 Ваш профиль</b>\n\n"
            f"<b>ID:</b> <code>{profile_data['user_id']}</code>\n"
            f"<b>Никнейм:</b> @{username}\n\n"
            f"<b>📊 Статистика:</b>\n"
            f"  - <b>Всего обменов:</b> {profile_data['total_orders']}\n"
            f"  - <b>Общий объем:</b> {profile_data['total_volume_rub']:.2f} RUB"
        )
    else:
        # Если профиль не найден
        text = "Не удалось найти ваш профиль. Возможно, вы еще не совершали обменов."

    # Проверяем, как был вызван хендлер (командой или кнопкой)
    if isinstance(event, Message):
        # Если это команда, просто отправляем ответ
        await event.answer(text, reply_markup=keyboard ,parse_mode="HTML")
    elif isinstance(event, CallbackQuery):
        # Если это кнопка, отправляем ответ в чат
        await event.message.answer(text, reply_markup=keyboard ,parse_mode="HTML")
        # И удаляем предыдущее сообщение с кнопками для чистоты
        try:
            await event.message.delete()
        except Exception as e:
            logger.warning(f"Could not delete message: {e}")
