# handlers/orders.py
"""
История заказов пользователя с пагинацией.
"""

from aiogram import Router
from aiogram.types import CallbackQuery

from config import ORDER_NUMBER_OFFSET
from utils.logging_config import logger
from utils.callbacks import OrdersPage
from utils.keyboards import get_orders_pagination_keyboard
from utils.database.db_helpers import acquire
from utils.database.db_queries import get_user_orders_page, count_user_orders

router = Router()

_PER_PAGE = 5

_STATUS_LABELS = {
    'processing': '⏳ В обработке',
    'completed': '✅ Завершена',
    'rejected': '❌ Отклонена',
    'cancelled_by_user': '🚫 Отменена вами',
    'auto_closed': '⌛ Закрыта авто',
}

_ACTION_LABELS = {
    'buy': '🛒 Купить',
    'sell': '💸 Продать',
}


def _format_orders_text(orders: list, page: int, total: int) -> str:
    if not orders:
        return "📋 <b>История заказов</b>\n\nУ вас пока нет заказов."

    total_pages = max(1, (total + _PER_PAGE - 1) // _PER_PAGE)
    lines = [f"📋 <b>История заказов</b> (стр. {page + 1}/{total_pages})\n"]

    for order in orders:
        order_number = order['order_id'] + ORDER_NUMBER_OFFSET
        action = _ACTION_LABELS.get(order['action'], order['action'])
        status = _STATUS_LABELS.get(order['status'], order['status'])
        created = order['created_at'].strftime('%d.%m.%Y %H:%M') if order['created_at'] else '—'
        lines.append(
            f"<b>#{order_number}</b> | {action} {order['crypto']}\n"
            f"  Сумма: <b>{float(order['amount_rub']):,.0f} RUB</b>\n"
            f"  Статус: {status}\n"
            f"  Дата: {created}\n"
        )

    return "\n".join(lines)


@router.callback_query(OrdersPage.filter())
async def orders_history_handler(callback: CallbackQuery, callback_data: OrdersPage):
    user_id = callback.from_user.id
    page = callback_data.page

    try:
        async with acquire() as conn:
            total = await count_user_orders(conn, user_id)
            orders = await get_user_orders_page(conn, user_id, limit=_PER_PAGE, offset=page * _PER_PAGE)
    except Exception as e:
        logger.error(f"DB error in orders_history_handler for user {user_id}: {e}", exc_info=True)
        await callback.answer("Ошибка при загрузке истории заказов.", show_alert=True)
        return

    text = _format_orders_text(orders, page, total)
    keyboard = get_orders_pagination_keyboard(page, total, _PER_PAGE)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()
