# Файл: handlers/admin/panel.py

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.filters import AdminFilter
from utils.states import BroadcastStates, AdminPromoStates
from utils.keyboards import get_admin_keyboard # Убедитесь, что эти стейты в utils/states.py

router = Router()
# Применяем фильтр ко всем хендлерам в этом файле
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

@router.callback_query(F.data == "back_to_admin_panel")
async def back_to_admin_panel_handler(call: CallbackQuery):
    """Возвращает в главное меню админа."""
    await call.message.edit_text(
        "👋 <b>Добро пожаловать в панель администратора!</b>\n\nВыберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@router.message(Command("admin"))
async def admin_panel_handler(message: Message):
    """Отображает главную панель администратора."""
    await message.answer(
        "👋 <b>Добро пожаловать в панель администратора!</b>\n\nВыберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    
    
    



# --- Обработчики кнопок главной панели ---

@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast_handler(call: CallbackQuery, state: FSMContext):
    """Начинает процесс создания рассылки."""
    await state.set_state(BroadcastStates.waiting_for_message)
    await call.message.edit_text("Пожалуйста, отправьте сообщение для рассылки (фото, видео или текст).")
    await call.answer()

@router.callback_query(F.data == "admin_create_promo")
async def start_promo_creation_handler(call: CallbackQuery, state: FSMContext):
    """Начинает процесс создания промокода."""
    await state.set_state(AdminPromoStates.waiting_for_promo_data)
    await call.message.edit_text(
        "Введите данные в формате: <b>ПРОМОКОД,КОЛИЧЕСТВО,СКИДКА</b>\n"
        "Например: <code>FREE2025,50,100</code>\n\n"
        "Тип скидки выберете на следующем шаге.",
        parse_mode="HTML"
    )
    await call.answer()