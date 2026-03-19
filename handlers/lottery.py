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
from utils.database.db_helpers import transaction
from utils.database.db_queries import get_user_lottery_info, grant_daily_ticket, play_lottery
from utils.helpers import calculate_lottery_win
import utils.texts as texts
import utils.keyboards as keyboards

router = Router()


async def _render_lottery_menu(message, user_id: int) -> None:
    """Обновляет сообщение с меню лотереи. Не трогает callback."""
    now = datetime.now()
    logger.debug("[LOTTERY] _render_lottery_menu: user_id=%s", user_id)

    async with transaction() as conn:
        logger.debug("[LOTTERY] fetching lottery_info from DB")
        lottery_info = await get_user_lottery_info(conn, user_id)
        logger.debug("[LOTTERY] lottery_info=%s", lottery_info)

        last_ticket_time = lottery_info.get('last_ticket')
        logger.debug("[LOTTERY] last_ticket_time=%s", last_ticket_time)

        can_get_new_ticket = False
        if not last_ticket_time or (now - last_ticket_time.replace(tzinfo=None)) > timedelta(hours=24):
            logger.debug("[LOTTERY] granting daily ticket")
            await grant_daily_ticket(conn, user_id)
            can_get_new_ticket = True
            lottery_info['last_ticket'] = now
            logger.debug("[LOTTERY] ticket granted")
        else:
            logger.debug("[LOTTERY] ticket already granted within 24h")

    last_play_time = lottery_info.get('last_play')
    logger.debug("[LOTTERY] last_play_time=%s", last_play_time)

    can_play = not last_play_time or (now - last_play_time.replace(tzinfo=None)) > timedelta(hours=24)
    logger.debug("[LOTTERY] can_get_new_ticket=%s  can_play=%s", can_get_new_ticket, can_play)

    text = texts.get_lottery_menu_text(lottery_info, can_get_new_ticket)
    keyboard = keyboards.get_lottery_menu_keyboard(can_get_new_ticket and can_play)
    logger.debug("[LOTTERY] text and keyboard built, editing message")

    try:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        logger.debug("[LOTTERY] message edited successfully")
    except AiogramError as e:
        logger.warning("[LOTTERY] edit_text failed (non-critical): %s", e)


@router.callback_query(F.data == "lottery_menu")
async def lottery_menu_handler(callback: CallbackQuery):
    """Показывает меню лотереи, проверяет и выдает ежедневный билет."""
    user_id = callback.from_user.id
    logger.debug("[LOTTERY] lottery_menu_handler triggered: user_id=%s", user_id)

    try:
        await _render_lottery_menu(callback.message, user_id)
        logger.debug("[LOTTERY] lottery_menu_handler: answering callback")
        await callback.answer()
        logger.debug("[LOTTERY] lottery_menu_handler: done")
    except Exception as e:
        logger.error("[LOTTERY] lottery_menu_handler ERROR for user %s: %s", user_id, e, exc_info=True)
        try:
            await callback.answer("Ошибка при загрузке данных лотереи!", show_alert=True)
        except Exception as e2:
            logger.error("[LOTTERY] callback.answer also failed: %s", e2)


@router.callback_query(F.data == "lottery_play")
async def lottery_play_handler(callback: CallbackQuery):
    """Обрабатывает нажатие на кнопку 'Испытать удачу!'."""
    user_id = callback.from_user.id
    now = datetime.now()
    logger.debug("[LOTTERY] lottery_play_handler triggered: user_id=%s", user_id)

    try:
        async with transaction() as conn:
            logger.debug("[LOTTERY] fetching lottery_info for play check")
            lottery_info = await get_user_lottery_info(conn, user_id)
            last_ticket_time = lottery_info.get('last_ticket')
            last_play_time = lottery_info.get('last_play')
            logger.debug("[LOTTERY] last_ticket=%s  last_play=%s", last_ticket_time, last_play_time)

            can_get_ticket = last_ticket_time and (now - last_ticket_time.replace(tzinfo=None)) < timedelta(hours=24)
            can_play = not last_play_time or (now - last_play_time.replace(tzinfo=None)) > timedelta(hours=24)
            logger.debug("[LOTTERY] can_get_ticket=%s  can_play=%s", can_get_ticket, can_play)

            if not (can_get_ticket and can_play):
                logger.debug("[LOTTERY] play not allowed, answering with alert")
                await callback.answer(
                    "Вы уже играли сегодня или у вас нет билета. Попробуйте завтра.",
                    show_alert=True,
                )
                return

            prize_amount = calculate_lottery_win(LOTTERY_PRIZES)
            logger.debug("[LOTTERY] prize_amount=%s, saving play to DB", prize_amount)
            await play_lottery(conn, user_id, prize_amount)
            logger.debug("[LOTTERY] play saved to DB")

        # Отвечаем на callback ДО анимации и ДО render_lottery_menu
        logger.debug("[LOTTERY] answering callback before animation")
        await callback.answer()

        try:
            dice_msg = await callback.bot.send_dice(chat_id=user_id, emoji="🎰")
            logger.debug("[LOTTERY] dice sent")
            await asyncio.sleep(3.5)
            await dice_msg.delete()
            logger.debug("[LOTTERY] dice deleted")
        except AiogramError as e:
            logger.warning("[LOTTERY] dice animation error (non-critical): %s", e)

        win_text = texts.get_lottery_win_text(prize_amount)
        await callback.message.answer(win_text, parse_mode="HTML")
        logger.debug("[LOTTERY] win text sent")

        # Обновляем меню лотереи — НЕ передаём callback (он уже закрыт)
        logger.debug("[LOTTERY] rendering updated lottery menu")
        await _render_lottery_menu(callback.message, user_id)
        logger.debug("[LOTTERY] lottery_play_handler: done")

    except Exception as e:
        logger.error("[LOTTERY] lottery_play_handler ERROR for user %s: %s", user_id, e, exc_info=True)
        try:
            await callback.answer("Произошла ошибка во время игры!", show_alert=True)
        except Exception as e2:
            logger.error("[LOTTERY] callback.answer also failed: %s", e2)
