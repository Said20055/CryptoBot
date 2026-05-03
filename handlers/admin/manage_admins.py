from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, BotCommand, BotCommandScopeChat
from aiogram.exceptions import AiogramError

import utils.admin_cache as admin_cache
from utils.callbacks import AdminManageAction
from utils.filters import AdminFilter
from utils.keyboards import back_to_admin_panel, get_manage_admins_keyboard
from utils.logging_config import logger
from utils.states import ManageAdminStates
from utils.database.db_helpers import acquire, transaction
from utils.database.db_queries import delete_admin, get_all_admins, upsert_admin

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

_ADMIN_COMMANDS = [
    BotCommand(command="/start", description="Запустить бота"),
    BotCommand(command="/profile", description="Показать мой профиль"),
    BotCommand(command="/promo", description="Активировать промокод"),
    BotCommand(command="/admin", description="Admin panel"),
]


async def _show_admins_list(target: CallbackQuery) -> None:
    async with acquire() as conn:
        admins = await get_all_admins(conn)
    env_ids = admin_cache.all_ids() & frozenset(
        uid for uid in admin_cache.all_ids() if admin_cache.is_env_admin(uid)
    )
    text = "<b>👥 Управление администраторами</b>\n\n"
    if admins:
        lines = []
        for a in admins:
            uid = a['user_id']
            mark = "👑" if admin_cache.is_env_admin(uid) else "👤"
            lines.append(f"{mark} {a['username'] or uid} (<code>{uid}</code>)")
        text += "\n".join(lines)
    else:
        text += "Список пуст."
    await target.message.edit_text(
        text,
        reply_markup=get_manage_admins_keyboard(admins, frozenset(
            a['user_id'] for a in admins if admin_cache.is_env_admin(a['user_id'])
        )),
        parse_mode="HTML",
    )
    await target.answer()


@router.callback_query(F.data == "admin_manage_admins")
async def admin_manage_admins_handler(callback: CallbackQuery) -> None:
    await _show_admins_list(callback)


@router.callback_query(F.data == "admin_add_admin")
async def admin_add_admin_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ManageAdminStates.waiting_for_user_id)
    await callback.message.edit_text(
        "Введите <b>user_id</b> нового администратора (только цифры):",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ManageAdminStates.waiting_for_user_id)
async def admin_add_admin_input(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    text = message.text.strip() if message.text else ""
    if not text.isdigit():
        await message.answer("Неверный формат. Введите числовой user_id.", reply_markup=back_to_admin_panel())
        return

    new_admin_id = int(text)
    if admin_cache.contains(new_admin_id):
        await message.answer("Этот пользователь уже является администратором.", reply_markup=back_to_admin_panel())
        return

    try:
        chat = await bot.get_chat(new_admin_id)
        username = chat.username or chat.full_name or str(new_admin_id)
    except Exception:
        username = str(new_admin_id)

    async with transaction() as conn:
        await upsert_admin(conn, new_admin_id, username, message.from_user.id)

    admin_cache.add(new_admin_id)

    try:
        await bot.set_my_commands(_ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=new_admin_id))
    except AiogramError as e:
        logger.warning(f"Could not set admin commands for {new_admin_id}: {e}")

    logger.info(f"Admin {message.from_user.id} added new admin {new_admin_id} (@{username})")
    await message.answer(
        f"✅ Пользователь <b>{username}</b> (<code>{new_admin_id}</code>) добавлен как администратор.",
        reply_markup=back_to_admin_panel(),
        parse_mode="HTML",
    )


@router.callback_query(AdminManageAction.filter(F.action == "remove"))
async def admin_remove_admin_handler(callback: CallbackQuery, callback_data: AdminManageAction) -> None:
    target_id = callback_data.user_id

    if admin_cache.is_env_admin(target_id):
        await callback.answer("Нельзя удалить постоянного администратора.", show_alert=True)
        return

    if not admin_cache.remove(target_id):
        await callback.answer("Не удалось удалить администратора.", show_alert=True)
        return

    async with transaction() as conn:
        await delete_admin(conn, target_id)

    logger.info(f"Admin {callback.from_user.id} removed admin {target_id}")
    await _show_admins_list(callback)


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()
