from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ORDER_NUMBER_OFFSET
from utils.callbacks import UserBlockAction
from utils.filters import AdminFilter
from utils.keyboards import back_to_admin_panel, get_user_info_keyboard
from utils.logging_config import logger
from utils.states import UserManageStates
from utils.database.db_helpers import acquire, transaction
from utils.database.db_queries import block_user, get_admin_user_profile, unblock_user

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

_STATUS_ICONS = {
    'completed': '✅',
    'processing': '⏳',
    'rejected': '❌',
    'cancelled_by_user': '🚫',
    'auto_closed': '⏱',
}


def _format_profile(data: dict) -> str:
    u = data['user']
    o = data['orders']
    w = data['withdrawals']

    name_parts = []
    if u['username']:
        name_parts.append(f"@{u['username']}")
    if u['full_name']:
        name_parts.append(u['full_name'])
    display_name = " / ".join(name_parts) if name_parts else "—"

    reg_date = u['created_at'].strftime("%d.%m.%Y") if u['created_at'] else "—"
    status = "🚫 Заблокирован" if u['is_blocked'] else "✅ Активен"

    # Referrer line
    ref = data['referrer']
    if ref:
        ref_name = f"@{ref['username']}" if ref['username'] else (ref['full_name'] or str(ref['user_id']))
        referrer_line = f"{ref_name} (<code>{ref['user_id']}</code>)"
    else:
        referrer_line = "—"

    # Recent orders
    recent_lines = []
    for r in data['recent_orders']:
        num = r['order_id'] + ORDER_NUMBER_OFFSET
        icon = _STATUS_ICONS.get(r['status'], '•')
        recent_lines.append(
            f"  {icon} #{num} {r['action'].upper()} {r['crypto']} — {float(r['amount_rub']):,.0f} ₽"
        )
    recent_str = "\n".join(recent_lines) if recent_lines else "  нет заявок"

    # Referral earnings history
    earnings_lines = []
    for e in data['earnings_history']:
        dt = e['created_at'].strftime("%d.%m.%Y") if e['created_at'] else "—"
        earnings_lines.append(f"  +{float(e['amount']):,.2f} RUB  ({dt}, от <code>{e['referral_id']}</code>)")
    earnings_str = "\n".join(earnings_lines) if earnings_lines else "  нет начислений"

    # Promo and lottery
    promo = u['activated_promo'] or "—"
    lottery = u['last_lottery_play'].strftime("%d.%m.%Y %H:%M") if u['last_lottery_play'] else "—"

    return (
        f"👤 <b>{display_name}</b>\n"
        f"🆔 ID: <code>{u['user_id']}</code>\n"
        f"📅 Зарегистрирован: {reg_date}\n"
        f"🚦 Статус: {status}\n"
        f"\n<b>── Финансы ──</b>\n"
        f"💰 Реф. баланс: <b>{float(u['referral_balance']):,.2f} RUB</b>\n"
        f"📈 Всего заработано: {float(data['total_earned']):,.2f} RUB\n"
        f"💸 Выведено: {float(w['total_withdrawn']):,.2f} RUB"
        f"  |  Ожидает: {float(w['pending']):,.2f} RUB\n"
        f"\n<b>── Сделки ──</b>\n"
        f"📦 Всего заявок: <b>{o['total']}</b>"
        f"  (✅ {o['completed']} / ❌ {o['cancelled']} / ⏳ {o['processing']})\n"
        f"💵 Объём: {float(o['total_volume']):,.2f} RUB\n"
        f"🕐 Последние:\n{recent_str}\n"
        f"\n<b>── Рефералы ──</b>\n"
        f"👥 Приглашено: {data['referral_count']}\n"
        f"👆 Приглашён: {referrer_line}\n"
        f"\n<b>── История реф. начислений (последние 10) ──</b>\n"
        f"{earnings_str}\n"
        f"\n<b>── Прочее ──</b>\n"
        f"🎁 Промокод: {promo}\n"
        f"🎰 Последняя лотерея: {lottery}"
    )


@router.callback_query(F.data == "admin_manage_users")
async def admin_manage_users_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(UserManageStates.waiting_for_user_id)
    await callback.message.edit_text(
        "Введите <b>user_id</b> пользователя:",
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
        data = await get_admin_user_profile(conn, user_id)

    if not data:
        await message.answer(
            f"Пользователь <code>{user_id}</code> не найден в базе.",
            reply_markup=back_to_admin_panel(),
            parse_mode="HTML",
        )
        return

    await message.answer(
        _format_profile(data),
        reply_markup=get_user_info_keyboard(user_id, bool(data['user']['is_blocked'])),
        parse_mode="HTML",
    )


@router.callback_query(UserBlockAction.filter())
async def user_block_action_handler(callback: CallbackQuery, callback_data: UserBlockAction) -> None:
    uid = callback_data.user_id
    action = callback_data.action

    async with transaction() as conn:
        if action == "block":
            await block_user(conn, uid)
            verb = "заблокирован"
        else:
            await unblock_user(conn, uid)
            verb = "разблокирован"

    logger.info(f"Admin {callback.from_user.id} {verb} user {uid}")

    async with acquire() as conn:
        data = await get_admin_user_profile(conn, uid)

    if data:
        await callback.message.edit_text(
            _format_profile(data),
            reply_markup=get_user_info_keyboard(uid, bool(data['user']['is_blocked'])),
            parse_mode="HTML",
        )
    await callback.answer(f"Пользователь {verb}.")
