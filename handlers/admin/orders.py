from asyncio.log import logger
from aiogram import Router
import aiosqlite
from aiogram.exceptions import AiogramError
from aiogram import F
from aiogram.types import CallbackQuery
from config import REFERRAL_PERCENTAGE
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import add_referral_earning, get_order_by_id, refund_promo_if_needed, update_order_status, use_activated_promo

orders_router = Router()

@orders_router.callback_query(F.data.startswith('confirm_order_'))
async def confirm_order_handler(callback_query: CallbackQuery):
    """Обрабатывает подтверждение заявки админом (ФИНАЛЬНАЯ ВЕРСИЯ)."""
    parts = callback_query.data.split('_')
    
    if len(parts) != 4:
        logger.error(f"Invalid callback data format for confirm_order: {callback_query.data}")
        await callback_query.answer("Ошибка в данных кнопки! Неверный формат.", show_alert=True, parse_mode="HTML")
        return

    try:
        _, _, order_id_str, user_id_str = parts
        order_id = int(order_id_str)
        user_id = int(user_id_str)
    except ValueError:
        logger.error(f"Could not parse ID from callback: {callback_query.data}")
        await callback_query.answer("Не удалось извлечь ID из данных кнопки!", show_alert=True, parse_mode="HTML")
        return
    
    # --- НОВЫЙ ПАТТЕРН РАБОТЫ С БД ---
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # Передаем курсор в функцию
                order_info = await get_order_by_id(cursor, order_id)
                order_amount = order_info['amount_rub']
                if order_info['status'] != 'processing':
                    await callback_query.answer("Заявка уже выполнена или отменена", show_alert=True, parse_mode="HTML")
                    return
                await update_order_status(cursor, order_id, "completed")
                await use_activated_promo(cursor, user_id, order_id)
                await add_referral_earning(
                    cursor,
                    order_id=order_id,
                    referral_id=user_id, # ID того, кто совершил сделку
                    order_amount=order_amount,
                    percentage=REFERRAL_PERCENTAGE
                )
                await db.commit()
    except Exception as e:
        logger.error(f"DB error in confirm_order_handler for order #{order_id}: {e}", exc_info=True)
        await callback_query.answer("Ошибка базы данных при списании промокода!", show_alert=True, parse_mode="HTML")
        return
    # --- КОНЕЦ НОВОГО ПАТТЕРНА ---
        
    order_number = order_id + 9999
    
    try:
        
        await callback_query.message.edit_text(
            f"{callback_query.message.text} Статус: <b>✅ЗАВЕРШЕНО</b>*",
            parse_mode="HTML"
        )
        await callback_query.answer(f"Заявка #{order_number} подтверждена.", show_alert=True, parse_mode="HTML")
        
        try:
            await callback_query.bot.send_message(
            chat_id=user_id,
            text=f"<b>✅ Ваша заявка</b> `#{order_number}` была *успешно завершена* оператором.",
            parse_mode="HTML"
        )
        except Exception as e:
            pass
    except AiogramError as e:
        await callback_query.answer(f"Не удалось уведомить пользователя {user_id}. Ошибка: {e}", show_alert=True, parse_mode="HTML")
        logger.error(f"Failed to notify user {user_id} about order confirmation: {e}")

@orders_router.callback_query(F.data.startswith('reject_order_'))
async def reject_order_handler(callback_query: CallbackQuery):
    """Обрабатывает отмену заявки админом и 'возвращает' промокод (ФИНАЛЬНАЯ ВЕРСИЯ)."""
    parts = callback_query.data.split('_')
    
    if len(parts) != 4:
        logger.error(f"Invalid callback data format for reject_order: {callback_query.data}")
        await callback_query.answer("Ошибка в данных кнопки! Неверный формат.", show_alert=True, parse_mode="HTML")
        return

    try:
        _, _, order_id_str, user_id_str = parts
        order_id = int(order_id_str)
        user_id = int(user_id_str)
    except ValueError:
        logger.error(f"Could not parse ID from callback: {callback_query.data}")
        await callback_query.answer("Не удалось извлечь ID из данных кнопки!", show_alert=True, parse_mode="HTML")
        return

    # --- НОВЫЙ ПАТТЕРН РАБОТЫ С БД ---
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # Передаем курсор в функцию
                order_info = await get_order_by_id(cursor, order_id)
                if order_info['status'] != 'processing':
                    await callback_query.answer("Заявка уже выполнена или отменена", show_alert=True, parse_mode="HTML")
                    return
                await update_order_status(cursor, order_id, "rejected")
                await refund_promo_if_needed(cursor, user_id, order_id)
                await db.commit()
    except Exception as e:
        logger.error(f"DB error in reject_order_handler for order #{order_id}: {e}", exc_info=True)
        await callback_query.answer("Ошибка базы данных при возврате промокода!", show_alert=True, parse_mode="HTML")
        return
    # --- КОНЕЦ НОВОГО ПАТТЕРНА ---
    
    order_number = order_id + 9999

    try:
        
        await callback_query.message.edit_text(
            f"{callback_query.message.text} Статус: <b> ❌ ОТМЕНЕНО</b>*",
            parse_mode="HTML"
        )
        await callback_query.answer(f"Заявка #{order_number} отменена. Промокод (если был) возвращен.", show_alert=True, parse_mode="HTML")
        try:
            await callback_query.bot.send_message(
            chat_id=user_id,
            text=f"<b>❌ Ваша заявка</b> `#{order_number}` была *отменена* оператором.",
            parse_mode="HTML"
        )
        except Exception as e:
            pass
    except AiogramError as e:
        await callback_query.answer(f"Не удалось уведомить пользователя {user_id}. Ошибка: {e}", show_alert=True, parse_mode="HTML")
        logger.error(f"Failed to notify user {user_id} about order rejection: {e}")
