# handlers/lottery.py

"""
Обработчики для модуля ежедневной лотереи.
"""
import asyncio
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import AiogramError

from config import LOTTERY_PRIZES
from utils.logging_config import logger
from utils.database.db_helpers import transaction, acquire
from utils.database.db_queries import get_user_lottery_info, grant_daily_ticket, play_lottery
from utils.helpers import calculate_lottery_win
import utils.texts as texts
import utils.keyboards as keyboards

router = Router()


@router.callback_query(F.data == "lottery_menu")
async def lottery_menu_handler(callback: CallbackQuery):
    """Показывает меню лотереи, проверяет и выдает ежедневный билет."""
    user_id = callback.from_user.id
    now = datetime.now()

    try:
        async with transaction() as conn:
            lottery_info = await get_user_lottery_info(conn, user_id)
            last_ticket_time = lottery_info.get('last_ticket')

            can_get_new_ticket = False
            if not last_ticket_time or (now - last_ticket_time.replace(tzinfo=None)) > timedelta(hours=24):
                await grant_daily_ticket(conn, user_id)
                can_get_new_ticket = True
                lottery_info['last_ticket'] = now

        last_play_time = lottery_info.get('last_play')
        can_play = not last_play_time or (now - last_play_time.replace(tzinfo=None)) > timedelta(hours=24)

        text = texts.get_lottery_menu_text(lottery_info, can_get_new_ticket)
        keyboard = keyboards.get_lottery_menu_keyboard(can_get_new_ticket and can_play)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"DB error in lottery_menu_handler for user {user_id}: {e}", exc_info=True)
        await callback.answer("Ошибка при загрузке данных лотереи!", show_alert=True)
    finally:
        await callback.answer()


@router.callback_query(F.data == "lottery_play")
async def lottery_play_handler(callback: CallbackQuery):
    """Обрабатывает нажатие на кнопку 'Испытать удачу!'."""
    user_id = callback.from_user.id
    now = datetime.now()

    try:
        async with transaction() as conn:
            lottery_info = await get_user_lottery_info(conn, user_id)
            last_ticket_time = lottery_info.get('last_ticket')
            last_play_time = lottery_info.get('last_play')

            can_get_ticket = last_ticket_time and (now - last_ticket_time.replace(tzinfo=None)) < timedelta(hours=24)
            can_play = not last_play_time or (now - last_play_time.replace(tzinfo=None)) > timedelta(hours=24)

            if not (can_get_ticket and can_play):
                await callback.answer("Вы уже играли сегодня или у вас нет билета. Попробуйте завтра.", show_alert=True)
                return

            prize_amount = calculate_lottery_win(LOTTERY_PRIZES)
            await play_lottery(conn, user_id, prize_amount)

        try:
            dice_msg = await callback.bot.send_dice(chat_id=user_id, emoji="🎰")
            await asyncio.sleep(3.5)
            await dice_msg.delete()
        except AiogramError as e:
            logger.warning(f"Failed to send or delete dice animation for user {user_id}: {e}")

        win_text = texts.get_lottery_win_text(prize_amount)
        await callback.message.answer(win_text, parse_mode="HTML")

        await lottery_menu_handler(callback)
    except Exception as e:
        logger.error(f"DB error in lottery_play_handler for user {user_id}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка во время игры!", show_alert=True)
    finally:
        await callback.answer()
