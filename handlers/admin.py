"""
Админские хендлеры.

Этот модуль содержит обработчики для административных функций:
рассылки сообщений, ответы пользователям и другие админские команды.
"""

import os
from io import BytesIO

import pandas as pd
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

from config import ADMIN_CHAT_ID
from utils.logging_config import logger
from utils.database import find_all_users

# Определяем состояния для рассылки
class BroadcastStates(StatesGroup):
    waiting_for_message = State()

async def users_handler(message: Message):
    """Обработчик команды /users"""
    user_id = message.from_user.id
    if user_id not in ADMIN_CHAT_ID:
        await message.answer("Эта команда доступна только администраторам.")
        logger.info(f"User {user_id} attempted to use /users but is not an admin")
        return

    try:
        users = await find_all_users()
        if not users:
            await message.answer("Пользователи не найдены в базе данных.")
            logger.info("No users found in database for /users command")
            return

        # Создаём DataFrame из данных пользователей, исключая invite_link_issued и subscription_duration
        columns = ["user_id", "username", "full_name", "email", "is_subscribed", "subscription_end", "created_at"]
        df = pd.DataFrame(users, columns=["user_id", "username", "full_name", "email", "is_subscribed", "subscription_end", "created_at", "invite_link_issued", "subscription_duration"])
        df = df[columns]  # Убираем ненужные столбцы
        
        # Преобразуем столбцы для удобства чтения
        df["is_subscribed"] = df["is_subscribed"].apply(lambda x: "Да" if x else "Нет")
        # Преобразуем даты в строки, обрабатывая NaT и None
        df["subscription_end"] = pd.to_datetime(df["subscription_end"], errors='coerce').dt.strftime("%d.%m.%Y %H:%M:%S").fillna("Нет")
        df["created_at"] = pd.to_datetime(df["created_at"], errors='coerce').dt.strftime("%d.%m.%Y %H:%M:%S").fillna("Нет")

        # Создаём Excel-файл в памяти
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Users")
            worksheet = writer.sheets["Users"]
            
            # Определяем цвета и стили
            header_fill = PatternFill(start_color="4682B4", end_color="4682B4", fill_type="solid")  # Синий (SteelBlue)
            white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")  # Белый
            gray_fill = PatternFill(start_color="EAEAE9", end_color="EAEAE9", fill_type="solid")  # Светло-серый (#EAEAE9)
            header_font = Font(color="FFFFFF", bold=True)  # Белый текст, жирный шрифт
            header_alignment = Alignment(horizontal="center", vertical="center")
            # Определяем границы
            thin_border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
            
            # Применяем стили к заголовкам
            for col_num, column in enumerate(df.columns, 1):
                cell = worksheet.cell(row=1, column=col_num)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = header_alignment
                cell.border = thin_border
                
                # Настраиваем ширину столбца
                max_length = max(
                    df[column].astype(str).map(len).max(),  # Максимальная длина содержимого
                    len(str(column))  # Длина заголовка
                )
                adjusted_width = max_length + 2
                worksheet.column_dimensions[get_column_letter(col_num)].width = adjusted_width
            
            # Чередование цветов строк и добавление границ
            for row_num in range(2, len(df) + 2):
                fill = gray_fill if (row_num % 2 == 0) else white_fill
                for col_num in range(1, len(df.columns) + 1):
                    cell = worksheet.cell(row=row_num, column=col_num)
                    cell.fill = fill
                    cell.border = thin_border
            
            # Добавляем фильтры для сортировки
            worksheet.auto_filter.ref = f"A1:{get_column_letter(len(df.columns))}{len(df) + 1}"
        
        output.seek(0)
        
        # Отправляем файл админу
        file = BufferedInputFile(output.getvalue(), filename="users.xlsx")
        await message.answer_document(file, caption="Список пользователей из базы данных")
        logger.info(f"User {user_id} received users list as Excel file")
        
    except (IOError, ValueError, KeyError) as e:
        await message.answer("Ошибка при генерации списка пользователей. Пожалуйста, попробуйте позже.")
        logger.error(f"Failed to generate users list for user {user_id}: {e}")

async def log_handler(message: Message):
    """Обработчик команды /log"""
    user_id = message.from_user.id
    if user_id not in ADMIN_CHAT_ID:
        await message.answer("Эта команда доступна только администраторам.")
        logger.info(f"User {user_id} attempted to use /log but is not an admin")
        return

    log_file_path = "logging.log"
    try:
        if not os.path.exists(log_file_path):
            await message.answer("Файл логов не найден.")
            logger.info("Log file not found for /log command")
            return

        with open(log_file_path, "rb") as f:
            file = BufferedInputFile(f.read(), filename="bot.log")
            await message.answer_document(file, caption="Файл логов бота")
            logger.info(f"User {user_id} received log file")
    except (IOError, FileNotFoundError) as e:
        await message.answer("Ошибка при отправке файла логов. Пожалуйста, попробуйте позже.")
        logger.error(f"Failed to send log file to user {user_id}: {e}")

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
    class AdminReplyStates(StatesGroup):
        """Состояния для ответа админа пользователю."""
        waiting_for_reply_message = State()
    
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

async def admin_reply_message_handler(message: Message, state: FSMContext):
    """Обработчик сообщения админа для отправки пользователю.
    
    Args:
        message: Сообщение админа
        state: FSM состояние
    """
    user_id = message.from_user.id
    if user_id not in ADMIN_CHAT_ID:
        await message.answer("Эта функция доступна только администраторам.")
        await state.clear()
        return

    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    
    if not target_user_id:
        await message.answer("Ошибка: не найден ID пользователя.")
        await state.clear()
        return

    try:
        # Отправляем сообщение пользователю с кнопкой "Ответить оператору"
        from utils.texts import get_reply_to_operator_keyboard
        await message.bot.send_message(
            chat_id=target_user_id,
            text=f"💬 Сообщение от оператора:\n\n{message.text}",
            reply_markup=get_reply_to_operator_keyboard()
        )
        
        # Подтверждаем админу
        await message.answer(f"✅ Сообщение отправлено пользователю {target_user_id}")
        logger.info(f"Admin {user_id} sent message to user {target_user_id}")
        
    except (ConnectionError, TimeoutError) as e:
        await message.answer(f"❌ Не удалось отправить сообщение пользователю {target_user_id}")
        logger.error(f"Failed to send admin message to user {target_user_id}: {e}")
    
    await state.clear()

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
