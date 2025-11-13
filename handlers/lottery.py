# handlers/lottery.py

"""
Обработчики для модуля ежедневной лотереи.
"""
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import AiogramError

from config import LOTTERY_PRIZES
from utils.logging_config import logger
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import get_user_lottery_info, grant_daily_ticket, play_lottery
from utils.helpers import calculate_lottery_win
import utils.texts as texts

# Создаем роутер специально для лотереи
lottery_router = Router()


@lottery_router.callback_query(F.data == "lottery_menu")
async def lottery_menu_handler(callback: CallbackQuery):
    """
    Показывает главно-е меню лотереи, проверяет и выдает ежедневный билет.
    """
    user_id = callback.from_user.id
    now = datetime.now()
    
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # 1. Получаем текущую информацию о пользователе
                lottery_info = await get_user_lottery_info(cursor, user_id)
                last_ticket_time = lottery_info.get('last_ticket')
                
                # 2. Проверяем, можно ли выдать новый бесплатный билет
                can_get_new_ticket = False
                if not last_ticket_time or (now - last_ticket_time) > timedelta(hours=24):
                    # Если билета не было или прошло > 24ч, выдаем новый
                    await grant_daily_ticket(cursor, user_id)
                    can_get_new_ticket = True
                    # Обновляем информацию, чтобы показать актуальное состояние
                    lottery_info['last_ticket'] = now
                
                await db.commit()
                
                # 3. Проверяем, может ли пользователь играть (прошел ли кулдаун на игру)
                last_play_time = lottery_info.get('last_play')
                can_play = False
                if not last_play_time or (now - last_play_time) > timedelta(hours=24):
                    can_play = True

        # 4. Генерируем текст и клавиатуру на основе полученных данных
        text = texts.get_lottery_menu_text(lottery_info, can_get_new_ticket)
        # Кнопка "Играть" будет доступна, если можно получить билет И можно играть
        keyboard = texts.get_lottery_menu_keyboard(can_get_new_ticket and can_play)
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logger.error(f"DB error in lottery_menu_handler for user {user_id}: {e}", exc_info=True)
        await callback.answer("Ошибка при загрузке данных лотереи!", show_alert=True)
    finally:
        await callback.answer()


@lottery_router.callback_query(F.data == "lottery_play")
async def lottery_play_handler(callback: CallbackQuery):
    """Обрабатывает нажатие на кнопку 'Испытать удачу!'."""
    user_id = callback.from_user.id
    now = datetime.now()

    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # Двойная проверка перед игрой
                lottery_info = await get_user_lottery_info(cursor, user_id)
                last_ticket_time = lottery_info.get('last_ticket')
                last_play_time = lottery_info.get('last_play')

                # Проверяем, есть ли у юзера "билет на сегодня" и прошел ли кулдаун на игру
                can_get_ticket = last_ticket_time and (now - last_ticket_time) < timedelta(hours=24)
                can_play = not last_play_time or (now - last_play_time) > timedelta(hours=24)

                if not (can_get_ticket and can_play):
                    await callback.answer("Вы уже играли сегодня или у вас нет билета. Попробуйте завтра.", show_alert=True)
                    return
                
                # 1. Разыгрываем приз
                prize_amount = calculate_lottery_win(LOTTERY_PRIZES)
                
                # 2. Обновляем данные в БД: помечаем, что юзер сыграл, и начисляем выигрыш
                await play_lottery(cursor, user_id, prize_amount)
                
                await db.commit()

        # 3. Анимация! Отправляем эмодзи игрового автомата
        try:
            dice_msg = await callback.bot.send_dice(chat_id=user_id, emoji="🎰")
            # Ждем завершения анимации
            await asyncio.sleep(3.5)
            # Удаляем сообщение с анимацией
            await dice_msg.delete()
        except AiogramError as e:
            logger.warning(f"Failed to send or delete dice animation for user {user_id}: {e}")

        # 4. Поздравляем пользователя с выигрышем
        win_text = texts.get_lottery_win_text(prize_amount)
        await callback.message.answer(win_text, parse_mode="HTML")
        
        # Обновляем меню лотереи, чтобы показать таймер
        await lottery_menu_handler(callback)

    except Exception as e:
        logger.error(f"DB error in lottery_play_handler for user {user_id}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка во время игры!", show_alert=True)
    finally:
        await callback.answer()