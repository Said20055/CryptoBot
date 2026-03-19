# handlers/admin/promo.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from utils.filters import AdminFilter
from utils.states import AdminPromoStates
from utils.keyboards import get_promo_type_keyboard, back_to_admin_panel
from utils.database.db_helpers import transaction
from utils.database.db_queries import add_promo_code
from utils.logging_config import logger

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(AdminPromoStates.waiting_for_promo_data)
async def process_promo_data(message: Message, state: FSMContext):
    """Принимает CODE,USES,AMOUNT и предлагает выбрать тип скидки."""
    parts = [p.strip() for p in message.text.split(',')]
    if len(parts) != 3:
        await message.answer(
            "❌ Неверный формат. Введите:\n"
            "<b>ПРОМОКОД,КОЛИЧЕСТВО,СКИДКА</b>\n"
            "Например: <code>SALE10,100,10</code>",
            parse_mode="HTML",
        )
        return

    code, uses_str, discount_str = parts
    try:
        uses = int(uses_str)
        discount_amount = float(discount_str.replace(',', '.'))
        if uses <= 0 or discount_amount <= 0 or not code:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Промокод не может быть пустым, а количество и скидка должны быть положительными числами."
        )
        return

    await state.update_data(code=code.upper(), uses=uses, discount_amount=discount_amount)
    await state.set_state(AdminPromoStates.waiting_for_discount_type)
    await message.answer(
        f"Промокод: <code>{code.upper()}</code>\n"
        f"Использований: <b>{uses}</b>\n"
        f"Скидка: <b>{discount_amount:g}</b>\n\n"
        "Выберите тип скидки:",
        reply_markup=get_promo_type_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(AdminPromoStates.waiting_for_discount_type, F.data.in_({"promo_type_percent", "promo_type_fixed"}))
async def process_promo_type(call: CallbackQuery, state: FSMContext):
    """Сохраняет промокод с выбранным типом скидки."""
    discount_type = "percent" if call.data == "promo_type_percent" else "fixed"
    data = await state.get_data()
    code = data["code"]
    uses = data["uses"]
    discount_amount = data["discount_amount"]

    try:
        async with transaction() as conn:
            success = await add_promo_code(conn, code, uses, discount_amount, discount_type)
    except Exception as e:
        logger.error(f"DB error while creating promo code '{code}': {e}", exc_info=True)
        await call.message.edit_text("Произошла ошибка базы данных.")
        await state.clear()
        await call.answer()
        return

    if success:
        type_label = f"{discount_amount:g}%" if discount_type == "percent" else f"{discount_amount:g} RUB"
        await call.message.edit_text(
            f"✅ Промокод <code>{code}</code> создан.\n"
            f"Использований: <b>{uses}</b>, скидка: <b>{type_label}</b>",
            reply_markup=back_to_admin_panel(),
            parse_mode="HTML",
        )
    else:
        await call.message.edit_text(
            f"❌ Не удалось создать промокод <code>{code}</code>. Возможно, он уже существует.",
            reply_markup=back_to_admin_panel(),
            parse_mode="HTML",
        )

    await state.clear()
    await call.answer()
