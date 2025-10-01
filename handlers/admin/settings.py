# Файл: handlers/admin/settings.py

import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.filters import AdminFilter
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import get_all_settings, update_setting
import logging
settings_router = Router()
settings_router.message.filter(AdminFilter())
settings_router.callback_query.filter(AdminFilter())

class SettingsEditStates(StatesGroup):
    waiting_for_new_value = State()

async def get_settings_menu():
    """Генерирует сообщение и клавиатуру для меню настроек."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.cursor() as cursor:
            settings = await get_all_settings(cursor)
    
    builder = InlineKeyboardBuilder()
    text = "⚙️ <b>Управление реквизитами</b>\n\nТекущие значения:\n"
    
    # Динамически создаем текст и кнопки
    key_map = {
        'sbp_phone': '📞 Телефон СБП',
        'sbp_bank': '🏦 Банк СБП'
    }
    # Добавляем кошельки
    for key in settings:
        if key.startswith('wallet_'):
            key_map[key] = f"💰 Кошелек {key.replace('wallet_', '').upper()}"

    for key, name in key_map.items():
        value = settings.get(key, "Не задано")
        text += f" - <b>{name}:</b> <code>{value}</code>\n"
        builder.button(text=f"Изменить {name}", callback_data=f"edit_setting:{key}")

    builder.button(text="⬅️ Назад в админ-панель", callback_data="back_to_admin_panel")
    builder.adjust(1)
    return text, builder.as_markup()

@settings_router.callback_query(F.data == "admin_settings")
async def show_settings_menu(call: CallbackQuery):
    """Показывает меню управления реквизитами."""
    text, keyboard = await get_settings_menu()
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await call.answer()

@settings_router.callback_query(F.data.startswith("edit_setting:"))
async def edit_setting_prompt(call: CallbackQuery, state: FSMContext):
    """Запрашивает новое значение для выбранной настройки."""
    key_to_edit = call.data.split(":")[1]
    await state.update_data(key_to_edit=key_to_edit)
    await state.set_state(SettingsEditStates.waiting_for_new_value)
    
    await call.message.edit_text(f"Пожалуйста, отправьте новое значение для <code>{key_to_edit}</code>:", parse_mode="HTML")
    await call.answer()

@settings_router.message(SettingsEditStates.waiting_for_new_value)
async def process_new_setting_value(message: Message, state: FSMContext):
    """Сохраняет новое значение и показывает обновленное меню."""
    data = await state.get_data()
    key = data.get('key_to_edit')
    new_value = message.text
    
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                await update_setting(cursor, key, new_value)
                await db.commit()
    except Exception as e:
        logging.error(f"Failed to update setting {key}: {e}", exc_info=True)
        await message.answer("❌ Ошибка при обновлении настройки в базе данных.")
        await state.clear()
        return

    await message.answer(f"✅ Настройка <code>{key}</code> успешно обновлена!", parse_mode="HTML")
    await state.clear()
    
    # Показываем обновленное меню
    text, keyboard = await get_settings_menu()
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")