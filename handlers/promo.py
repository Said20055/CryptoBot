# handlers/promo.py
"""
Активация промокодов пользователем (/promo, кнопка «Промокод»).
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from utils.logging_config import logger
from utils.database.db_helpers import transaction
from utils.database.db_queries import activate_promo_for_user, get_promo_discount_info
from utils.states import PromoStates

router = Router()


@router.message(Command("promo"))
@router.callback_query(F.data == "activate_promo")
async def promo_entry_handler(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(PromoStates.waiting_for_promo_code)
    text = "Введите ваш промокод:"
    if isinstance(event, Message):
        await event.answer(text)
    else:
        await event.message.answer(text)
        await event.answer()


@router.message(PromoStates.waiting_for_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    code = message.text.strip()
    try:
        async with transaction() as conn:
            result = await activate_promo_for_user(conn, message.from_user.id, code)
            if result == "success":
                discount_amount, discount_type = await get_promo_discount_info(conn, code)
            else:
                discount_amount, discount_type = 0.0, 'percent'
    except Exception as e:
        logger.error(f"DB error during promo activation for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.")
        await state.clear()
        return

    if result == "success":
        type_label = "%" if discount_type == 'percent' else "RUB"
        await message.answer(
            f"✅ Промокод успешно активирован! Скидка на комиссии: "
            f"<b>{discount_amount:.0f} {type_label}</b> на следующий обмен.",
            parse_mode="HTML",
        )
    elif result == "invalid_or_expired":
        await message.answer(
            "❌ Такого промокода не существует, он неактивен, или у него закончились использования."
        )
    elif result == "already_active":
        await message.answer("⚠️ У вас уже есть другой активный промокод. Сначала используйте его.")
    elif result == "already_redeemed":
        await message.answer("⚠️ Вы уже использовали этот промокод ранее.")
    else:
        await message.answer("Произошла системная ошибка, попробуйте позже.")

    await state.clear()
