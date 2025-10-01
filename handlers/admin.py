"""
Админские хендлеры.

Этот модуль содержит обработчики для административных функций:
рассылки сообщений, ответы пользователям и другие админские команды.
"""

import os
from io import BytesIO
import aiosqlite
import pandas as pd
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import AiogramError
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

from config import ADMIN_CHAT_ID
from utils.logging_config import logger
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import add_promo_code, find_all_users, refund_promo_if_needed, update_order_status, use_activated_promo
from utils.states import PromoStates

# Определяем состояния для рассылки
class BroadcastStates(StatesGroup):
    waiting_for_message = State()


# Состояния для ответа админа пользователю (перенесены на уровень модуля)
class AdminReplyStates(StatesGroup):
    waiting_for_reply_message = State()

async def send_handler(message: Message, state: FSMContext):
    """Обработчик команды /send"""
    user_id = message.from_user.id
    if user_id not in ADMIN_CHAT_ID:
        await message.answer("Эта команда доступна только администраторам.")
        logger.info(f"User {user_id} attempted to use /send but is not an admin")
        return

    await message.answer(
        "Пожалуйста, отправьте текст для рассылки."
    )
    await state.set_state(BroadcastStates.waiting_for_message)

async def cancel_broadcast_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик отмены рассылки"""
    user_id = callback_query.from_user.id
    if user_id not in ADMIN_CHAT_ID:
        await callback_query.message.answer("Эта команда доступна только администраторам.")
        logger.info(f"User {user_id} attempted to cancel broadcast but is not an admin")
        await callback_query.message.delete()
        return

    await state.clear()
    await callback_query.message.answer("Рассылка отменена.")
    logger.info(f"User {user_id} cancelled broadcast")
    await callback_query.message.delete()

async def admin_reply_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик кнопки ответа админа пользователю.
    
    Args:
        callback_query: Callback query от нажатия кнопки "Ответить пользователю"
        state: FSM состояние
    """
    user_id = callback_query.from_user.id
    if user_id not in ADMIN_CHAT_ID:
        await callback_query.answer("Эта функция доступна только администраторам.")
        return

    # Извлекаем target_user_id из callback_data
    try:
        target_user_id = int(callback_query.data.split('_')[2])
    except (ValueError, IndexError):
        await callback_query.answer("Ошибка получения ID пользователя.")
        return

    # Сохраняем target_user_id в состоянии
    await state.update_data(target_user_id=target_user_id)
    await state.set_state(AdminReplyStates.waiting_for_reply_message)
    
    await callback_query.message.answer(f"Напишите сообщение для пользователя {target_user_id}:")
    await callback_query.answer()


    
async def broadcast_message_handler(message: Message, state: FSMContext):
    """Обработчик рассылки сообщений"""
    user_id = message.from_user.id
    if user_id not in ADMIN_CHAT_ID:
        await message.answer("Эта команда доступна только администраторам.")
        logger.info(f"User {user_id} attempted to broadcast message but is not an admin")
        await state.clear()
        return

    broadcast_text = message.text
    try:
        users = await find_all_users()
        if not users:
            await message.answer("Пользователи не найдены в базе данных.")
            logger.info("No users found for broadcast")
            await state.clear()
            return

        successful = 0
        failed = 0
        failed_users = []

        for user in users:
            target_user_id = user[0]
            username = user[1] or user[2] or "Пользователь"  # user[1] = username, user[2] = full_name
            try:
                await message.bot.send_message(
                    chat_id=target_user_id,
                    text=broadcast_text,
                    parse_mode="Markdown"
                )
                successful += 1
                from utils.texts import format_user_display_name
                logger.info(f"Broadcast message sent to user {target_user_id} ({format_user_display_name(username)})")
            except (ConnectionError, TimeoutError) as e:
                failed += 1
                from utils.texts import format_user_display_name
                failed_users.append(f"{format_user_display_name(username)} (ID: {target_user_id})")
                logger.error(f"Failed to send broadcast to user {target_user_id}: {e}")

        # Отправляем отчёт админу, вызвавшему команду
        report = (
            f"Рассылка завершена.\n"
            f"Отправлено: {successful}\n"
            f"Не отправлено: {failed}\n"
        )
        if failed_users:
            report += "Не удалось отправить следующим пользователям:\n" + "\n".join(failed_users)
        await message.answer(report)
        logger.info(f"Broadcast report sent to admin {user_id}: {successful} successful, {failed} failed")

        # Уведомляем всех админов об отчёте
        for admin_id in ADMIN_CHAT_ID:
            if admin_id != user_id:  # Не отправляем отчёт админу, который инициировал рассылку
                try:
                    await message.bot.send_message(
                        chat_id=admin_id,
                        text=report,
                        parse_mode=None
                    )
                    logger.info(f"Broadcast report sent to admin {admin_id}")
                except (ConnectionError, TimeoutError) as e:
                    logger.error(f"Failed to send broadcast report to admin {admin_id}: {e}")

        await state.clear()
    except (ConnectionError, TimeoutError, ValueError) as e:
        await message.answer("Ошибка при выполнении рассылки. Пожалуйста, попробуйте позже.")
        logger.error(f"Failed to perform broadcast for user {user_id}: {e}")
        await state.clear()

async def add_promo_handler(message: Message, state: FSMContext):
    """Запрашивает у админа промокод и количество использований."""
    if message.from_user.id not in ADMIN_CHAT_ID: return
    await message.answer(
        "Введите данные в формате: <b>ПРОМОКОД,КОЛИЧЕСТВО</b>\n"
        "Например: <code>FREE2025,50</code> (это создаст код на 50 использований)",
        parse_mode="HTML"
    )
    await state.set_state(PromoStates.waiting_for_promo_code)

async def process_new_promo_code(message: Message, state: FSMContext):
    """Обрабатывает ввод, парсит и сохраняет новый промокод (ИСПРАВЛЕННАЯ ВЕРСИЯ)."""
    if message.from_user.id not in ADMIN_CHAT_ID: return
    
    parts = [p.strip() for p in message.text.split(',')]
    if len(parts) != 2:
        await message.answer("❌ Неверный формат. Введите: <b>ПРОМОКОД,КОЛИЧЕСТВО</b>", parse_mode="HTML")
        return

    code = parts[0].upper()
    try:
        uses = int(parts[1])
        if uses <= 0 or not code: raise ValueError
    except ValueError:
        await message.answer("❌ Промокод не может быть пустым, а количество - положительным числом.")
        return

    # --- НОВЫЙ ПАТТЕРН РАБОТЫ С БД ---
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # Передаем курсор как первый аргумент
                success = await add_promo_code(cursor, code, uses)
                await db.commit()
    except Exception as e:
        logger.error(f"DB error while creating promo code '{code}': {e}", exc_info=True)
        await message.answer("Произошла ошибка базы данных.")
        await state.clear()
        return
    # --- КОНЕЦ НОВОГО ПАТТЕРНА ---

    if success:
        await message.answer(f"✅ Промокод <code>{code}</code> на <b>{uses}</b> использований успешно создан.", parse_mode="HTML")
    else:
        await message.answer(f"❌ Не удалось создать промокод <code>{code}</code>. Возможно, он уже существует.", parse_mode="HTML")
    
    await state.clear()
    
async def confirm_order_handler(callback_query: CallbackQuery):
    """Обрабатывает подтверждение заявки админом (ФИНАЛЬНАЯ ВЕРСИЯ)."""
    parts = callback_query.data.split('_')
    
    if len(parts) != 4:
        logger.error(f"Invalid callback data format for confirm_order: {callback_query.data}")
        await callback_query.answer("Ошибка в данных кнопки! Неверный формат.", show_alert=True)
        return

    try:
        _, _, order_id_str, user_id_str = parts
        order_id = int(order_id_str)
        user_id = int(user_id_str)
    except ValueError:
        logger.error(f"Could not parse ID from callback: {callback_query.data}")
        await callback_query.answer("Не удалось извлечь ID из данных кнопки!", show_alert=True)
        return
    
    # --- НОВЫЙ ПАТТЕРН РАБОТЫ С БД ---
    promo_was_used = False
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # Передаем курсор в функцию
                await update_order_status(cursor, order_id, "completed")
                promo_was_used = await use_activated_promo(cursor, user_id, order_id)
                await db.commit()
    except Exception as e:
        logger.error(f"DB error in confirm_order_handler for order #{order_id}: {e}", exc_info=True)
        await callback_query.answer("Ошибка базы данных при списании промокода!", show_alert=True)
        return
    # --- КОНЕЦ НОВОГО ПАТТЕРНА ---
        
    order_number = order_id + 9999
    
    try:
        await callback_query.bot.send_message(
            chat_id=user_id,
            text=f"✅ Ваша заявка `#{order_number}` была *успешно завершена* оператором.",
            parse_mode="Markdown"
        )
        await callback_query.message.edit_text(
            f"{callback_query.message.text}\n\n*Статус: ✅ ЗАВЕРШЕНО*",
            parse_mode="Markdown"
        )
        await callback_query.answer(f"Заявка #{order_number} подтверждена.", show_alert=True)
        
        logger.info(f"Admin {callback_query.from_user.id} confirmed order #{order_number} (ID: {order_id}).")
        if promo_was_used:
            logger.info(f"Promo code for user {user_id} was used for order #{order_number}.")
            
    except AiogramError as e:
        await callback_query.answer(f"Не удалось уведомить пользователя {user_id}. Ошибка: {e}", show_alert=True)
        logger.error(f"Failed to notify user {user_id} about order confirmation: {e}")


async def reject_order_handler(callback_query: CallbackQuery):
    """Обрабатывает отмену заявки админом и 'возвращает' промокод (ФИНАЛЬНАЯ ВЕРСИЯ)."""
    parts = callback_query.data.split('_')
    
    if len(parts) != 4:
        logger.error(f"Invalid callback data format for reject_order: {callback_query.data}")
        await callback_query.answer("Ошибка в данных кнопки! Неверный формат.", show_alert=True)
        return

    try:
        _, _, order_id_str, user_id_str = parts
        order_id = int(order_id_str)
        user_id = int(user_id_str)
    except ValueError:
        logger.error(f"Could not parse ID from callback: {callback_query.data}")
        await callback_query.answer("Не удалось извлечь ID из данных кнопки!", show_alert=True)
        return

    # --- НОВЫЙ ПАТТЕРН РАБОТЫ С БД ---
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # Передаем курсор в функцию
                await update_order_status(cursor, order_id, "rejected")
                await refund_promo_if_needed(cursor, user_id, order_id)
                await db.commit()
    except Exception as e:
        logger.error(f"DB error in reject_order_handler for order #{order_id}: {e}", exc_info=True)
        await callback_query.answer("Ошибка базы данных при возврате промокода!", show_alert=True)
        return
    # --- КОНЕЦ НОВОГО ПАТТЕРНА ---
    
    order_number = order_id + 9999

    try:
        await callback_query.bot.send_message(
            chat_id=user_id,
            text=f"❌ Ваша заявка `#{order_number}` была *отменена* оператором. Если вы использовали промокод, он снова доступен для активации.",
            parse_mode="Markdown"
        )
        await callback_query.message.edit_text(
            f"{callback_query.message.text}\n\n*Статус: ❌ ОТМЕНЕНО*",
            parse_mode="Markdown"
        )
        await callback_query.answer(f"Заявка #{order_number} отменена. Промокод (если был) возвращен.", show_alert=True)
        logger.info(f"Admin {callback_query.from_user.id} rejected order #{order_number} (ID: {order_id}).")
    except AiogramError as e:
        await callback_query.answer(f"Не удалось уведомить пользователя {user_id}. Ошибка: {e}", show_alert=True)
        logger.error(f"Failed to notify user {user_id} about order rejection: {e}")