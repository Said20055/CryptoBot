# handlers/admin/orders.py

from aiogram import Router
from aiogram.exceptions import AiogramError
from aiogram.types import CallbackQuery

from config import ORDER_NUMBER_OFFSET, REFERRAL_PERCENTAGE
from utils.callbacks import AdminOrderAction
from utils.filters import AdminFilter
from utils.logging_config import logger
from utils.database.db_helpers import transaction
from utils.database.db_queries import (
    add_referral_earning, get_order_by_id, refund_promo_if_needed,
    update_order_status, use_activated_promo,
)

router = Router()
router.callback_query.filter(AdminFilter())


@router.callback_query(AdminOrderAction.filter())
async def handle_admin_order_action(callback: CallbackQuery, callback_data: AdminOrderAction):
    order_id = callback_data.order_id
    user_id = callback_data.user_id
    action = callback_data.action  # 'confirm' или 'reject'

    try:
        async with transaction() as conn:
            order_info = await get_order_by_id(conn, order_id)
            if not order_info or order_info['status'] != 'processing':
                await callback.answer("Заявка уже выполнена или отменена.", show_alert=True)
                return

            if action == "confirm":
                referral_base = order_info['service_commission_rub'] + order_info['network_fee_rub']
                await update_order_status(conn, order_id, "completed")
                await use_activated_promo(conn, user_id, order_id)
                await add_referral_earning(
                    conn, order_id=order_id, referral_id=user_id,
                    order_amount=referral_base, percentage=REFERRAL_PERCENTAGE,
                )
            else:
                await update_order_status(conn, order_id, "rejected")
                await refund_promo_if_needed(conn, user_id, order_id)
    except Exception as e:
        logger.error(f"DB error in handle_admin_order_action for order #{order_id}: {e}", exc_info=True)
        await callback.answer("Ошибка базы данных!", show_alert=True)
        return

    order_number = order_id + ORDER_NUMBER_OFFSET

    if action == "confirm":
        status_label = "✅ ЗАВЕРШЕНО"
        user_msg = f"<b>✅ Ваша заявка #{order_number}</b> была успешно завершена оператором."
        admin_answer = f"Заявка #{order_number} подтверждена."
    else:
        status_label = "❌ ОТМЕНЕНО"
        user_msg = f"<b>❌ Ваша заявка #{order_number}</b> была отменена оператором."
        admin_answer = f"Заявка #{order_number} отменена. Промокод (если был) возвращён."

    try:
        await callback.message.edit_text(
            f"{callback.message.text}\n\nСтатус: <b>{status_label}</b>",
            parse_mode="HTML",
        )
    except AiogramError:
        pass

    await callback.answer(admin_answer, show_alert=True)

    try:
        await callback.bot.send_message(chat_id=user_id, text=user_msg, parse_mode="HTML")
    except Exception:
        pass
