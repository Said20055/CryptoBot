from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from utils.callbacks import UserBlockAction
from utils.filters import AdminFilter
from utils.keyboards import back_to_admin_panel, get_user_info_keyboard
from utils.logging_config import logger
from utils.states import UserManageStates
from utils.database.db_helpers import acquire, transaction
from utils.database.db_queries import block_user, get_user_info, unblock_user

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.callback_query(F.data == "admin_manage_users")
async def admin_manage_users_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(UserManageStates.waiting_for_user_id)
    await callback.message.edit_text(
        "Введите <b>user_id</b> пользователя для просмотра и блокировки:",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(UserManageStates.waiting_for_user_id)
async def user_id_input_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = message.text.strip() if message.text else ""
    if not text.isdigit():
        await message.answer("Неверный формат. Введите числовой user_id.", reply_markup=back_to_admin_panel())
        return

    user_id = int(text)
    async with acquire() as conn:
        user = await get_user_info(conn, user_id)

    if not user:
        await message.answer(
            f"Пользователь <code>{user_id}</code> не найден в базе.",
            reply_markup=back_to_admin_panel(),
            parse_mode="HTML",
        )
        return

    is_blocked = bool(user['is_blocked'])
    status = "🚫 Заблокирован" if is_blocked else "✅ Активен"
    name = user['username'] or user['full_name'] or str(user_id)

    await message.answer(
        f"<b>Пользователь:</b> {name} (<code>{user_id}</code>)\n"
        f"<b>Статус:</b> {status}",
        reply_markup=get_user_info_keyboard(user_id, is_blocked),
        parse_mode="HTML",
    )


@router.callback_query(UserBlockAction.filter())
async def user_block_action_handler(callback: CallbackQuery, callback_data: UserBlockAction) -> None:
    uid = callback_data.user_id
    action = callback_data.action

    async with transaction() as conn:
        if action == "block":
            await block_user(conn, uid)
            label = "заблокирован"
            new_blocked = True
        else:
            await unblock_user(conn, uid)
            label = "разблокирован"
            new_blocked = False

    logger.info(f"Admin {callback.from_user.id} {label} user {uid}")

    async with acquire() as conn:
        user = await get_user_info(conn, uid)

    name = (user['username'] or user['full_name'] or str(uid)) if user else str(uid)
    status = "🚫 Заблокирован" if new_blocked else "✅ Активен"

    await callback.message.edit_text(
        f"<b>Пользователь:</b> {name} (<code>{uid}</code>)\n"
        f"<b>Статус:</b> {status}",
        reply_markup=get_user_info_keyboard(uid, new_blocked),
        parse_mode="HTML",
    )
    await callback.answer(f"Пользователь {label}.")
