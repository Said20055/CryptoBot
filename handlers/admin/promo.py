# Файл: handlers/admin/promo.py
import logging
import aiosqlite
from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from utils.filters import AdminFilter
from utils.states import PromoStates
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import add_promo_code

promo_router = Router()
promo_router.message.filter(AdminFilter()) # Защищаем FSM-хендлер

@promo_router.message(PromoStates.waiting_for_promo_code)
async def process_new_promo_code(message: Message, state: FSMContext):
    """Обрабатывает ввод, парсит и сохраняет новый промокод."""
    parts = [p.strip() for p in message.text.split(',')]
    if len(parts) != 2:
        await message.answer("❌ Неверный формат. Введите: <b>ПРОМОКОД,КОЛИЧЕСТВО</b>", parse_mode="HTML")
        return

    code, uses_str = parts
    try:
        uses = int(uses_str)
        if uses <= 0 or not code: raise ValueError
    except ValueError:
        await message.answer("❌ Промокод не может быть пустым, а количество - положительным числом.")
        return

    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                success = await add_promo_code(cursor, code.upper(), uses)
                await db.commit()
    except Exception as e:
        logging.error(f"DB error while creating promo code '{code}': {e}", exc_info=True)
        await message.answer("Произошла ошибка базы данных.")
        await state.clear()
        return

    if success:
        await message.answer(f"✅ Промокод <code>{code.upper()}</code> на <b>{uses}</b> использований создан.", parse_mode="HTML")
    else:
        await message.answer(f"❌ Не удалось создать промокод <code>{code.upper()}</code>. Возможно, он уже существует.", parse_mode="HTML")
    
    await state.clear()