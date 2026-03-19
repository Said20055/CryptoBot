# handlers/referral.py
"""
Реферальная система: история начислений, вывод баланса.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import MIN_WITHDRAWAL_AMOUNT, SUPPORT_GROUP_ID
from utils import keyboards, texts
from utils.logging_config import logger
from utils.database.db_helpers import acquire, transaction
from utils.database.db_queries import (
    create_withdrawal_request, get_referral_earnings_history, get_user_referral_info,
)
from utils.states import ReferralStates

router = Router()


@router.callback_query(F.data == "ref_earnings_history")
async def referral_earnings_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        async with acquire() as conn:
            ref_info = await get_user_referral_info(conn, user_id)
            earnings_history = await get_referral_earnings_history(conn, user_id)
    except Exception as e:
        logger.error(f"DB error in referral_earnings_handler for user {user_id}: {e}", exc_info=True)
        await callback.answer("Ошибка при загрузке истории. Попробуйте позже.", show_alert=True)
        return

    text = texts.get_referral_earnings_text(earnings_history, ref_info.get('balance', 0.0))
    await callback.message.edit_text(text, reply_markup=keyboards.get_back_to_main_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "ref_withdraw")
async def withdrawal_request_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    try:
        async with acquire() as conn:
            ref_info = await get_user_referral_info(conn, user_id)
    except Exception as e:
        logger.error(f"DB error in withdrawal_request_handler for user {user_id}: {e}", exc_info=True)
        await callback.answer("Ошибка базы данных!", show_alert=True)
        return

    balance = ref_info.get('balance', 0.0)
    if balance < MIN_WITHDRAWAL_AMOUNT:
        await callback.answer(
            f"Недостаточно средств. Мин. сумма для вывода: {MIN_WITHDRAWAL_AMOUNT} RUB.",
            show_alert=True,
        )
        return

    await state.update_data(withdrawal_amount=balance)
    await state.set_state(ReferralStates.waiting_for_withdrawal_details)
    await callback.message.answer(
        texts.get_withdrawal_prompt_text(MIN_WITHDRAWAL_AMOUNT, balance),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ReferralStates.waiting_for_withdrawal_details)
async def process_withdrawal_details(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_details = message.text.strip()
    fsm_data = await state.get_data()
    amount = fsm_data.get('withdrawal_amount')

    if not amount:
        await message.answer("Произошла ошибка, не найдена сумма вывода. Попробуйте снова.")
        await state.clear()
        return

    try:
        topic = await message.bot.create_forum_topic(
            chat_id=SUPPORT_GROUP_ID,
            name=f"Вывод {amount:,.0f} RUB для {message.from_user.full_name}",
        )
        async with transaction() as conn:
            await create_withdrawal_request(conn, user_id, amount, topic.message_thread_id)

        admin_text = texts.get_withdrawal_request_admin_notification(
            user_id, message.from_user.username, amount
        )
        await message.bot.send_message(
            chat_id=SUPPORT_GROUP_ID,
            message_thread_id=topic.message_thread_id,
            text=f"{admin_text}\n\n<b>Реквизиты пользователя:</b>\n<code>{user_details}</code>",
            parse_mode="HTML",
        )
        await message.answer(
            f"✅ Заявка на вывод <b>{amount:,.2f} RUB</b> создана!\n\n"
            "Оператор свяжется с вами для обработки выплаты. Ваш реферальный баланс был обнулён.",
            parse_mode="HTML",
        )
        logger.info(f"User {user_id} created withdrawal request for {amount:.2f} RUB.")
    except Exception as e:
        logger.error(f"Critical error in withdrawal process for user {user_id}: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла критическая ошибка при создании заявки на вывод. Сообщите оператору."
        )
    finally:
        await state.clear()
