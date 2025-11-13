# handlers/main.py (ВЕРСИЯ С ДЕКОРАТОРАМИ)

"""
Основные хендлеры для главного меню, профиля и промокодов.
"""
import aiosqlite
from typing import Union
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import AiogramError

# Импортируем наш роутер
from handlers.router import main_router as router

from config import ADMIN_CHAT_ID, MIN_WITHDRAWAL_AMOUNT, REFERRAL_PERCENTAGE, SUPPORT_GROUP_ID
from utils import texts
from utils.logging_config import logger
from utils.database.db_connector import DB_NAME
from utils.database.db_queries import activate_promo_for_user, create_withdrawal_request, get_referral_earnings_history, get_user_profile, get_user_referral_info, save_or_update_user
from utils.texts import WELCOME_PHOTO_URL, WELCOME_TEXT, format_user_display_name, get_profile_text
from utils import keyboards
from utils.states import ReferralStates, UserPromoStates




# =============================================================================
# --- БЛОК: СТАРТ / ГЛАВНОЕ МЕНЮ ---
# =============================================================================

async def _show_main_menu(event: Message | CallbackQuery, is_new_user: bool):
    """Внутренняя функция для отправки главного меню.
    Поддерживает и Message, и CallbackQuery.
    """
    # Для callback обязательно получить Message
    msg = event.message if isinstance(event, CallbackQuery) else event

    # Уведомление админам о новом пользователе
    if is_new_user:
        for admin_id in ADMIN_CHAT_ID:
            try:
                await msg.bot.send_message(
                    chat_id=admin_id,
                    text=f"Новый пользователь: @{msg.from_user.username or 'NoUsername'}\n"
                         f"Имя: {msg.from_user.full_name}\nID: {msg.from_user.id}"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id} about new user: {e}")

    # Отправка фото с главным меню
    await msg.answer_photo(
        photo=WELCOME_PHOTO_URL,
        text=WELCOME_TEXT,
        reply_markup=keyboards.get_main_keyboard(),
        parse_mode="HTML"
    )

    # Если это callback, обязательно ответить на него, чтобы исчез "часовой индикатор"
    if isinstance(event, CallbackQuery):
        await event.answer()

@router.message(Command(commands=['start']))
async def start_command_handler(message: Message):
    """
    Обрабатывает команду /start, включая реферальные ссылки (deep linking).
    """
    user_id = message.from_user.id
    username = message.from_user.username or "Нет username"
    full_name = message.from_user.full_name
    
    referrer_id = None
    
    # Извлекаем payload (то, что идет после /start)
    payload = message.text.split()[1] if len(message.text.split()) > 1 else None
    if payload and payload.startswith("ref"):
        try:
            referrer_id = int(payload[3:])
            logger.info(f"User {user_id} started bot with referrer ID: {referrer_id}")
            if referrer_id == user_id: # Защита от само-реферальства
                referrer_id = None
        except (ValueError, IndexError):
            logger.warning(f"Invalid referrer payload from user {user_id}: {payload}")
            referrer_id = None

    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                is_new_user = await save_or_update_user(cursor, user_id, username, full_name, referrer_id)
                await db.commit()
    except Exception as e:
        logger.error(f"DB error in start_handler for user {user_id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.")
        return
    
    await _show_main_menu(message, is_new_user)

@router.callback_query(F.data == 'back_to_main_menu')
async def back_to_main_menu_handler(callback_query: CallbackQuery):
    """Обработчик кнопки 'Назад в главное меню'."""
    # При возврате в меню нам не нужно снова сохранять пользователя
    await _show_main_menu(callback_query.message, is_new_user=False)
    try:
        await callback_query.message.delete()
    except AiogramError:
        pass
    await callback_query.answer()


# =============================================================================
# --- БЛОК: ПРОФИЛЬ ---
# =============================================================================


@router.message(Command(commands=['profile']))
async def profile_command_handler(message: Message):
    """Обработчик команды /profile."""
    user_id = message.from_user.id
    bot_username = (await message.bot.get_me()).username

    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                profile_data = await get_user_profile(cursor, user_id)
                ref_info = await get_user_referral_info(cursor, user_id)
    except Exception as e:
        logger.error(f"DB error in referral_handler for user {user_id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при загрузке ваших данных. Попробуйте позже.")
        return
    message_profile = get_profile_text(user_id= user_id,
                                  bot_username=bot_username,
                                  profile_data=profile_data,
                                  ref_info=ref_info,
                                  ref_percentage=REFERRAL_PERCENTAGE)
    
    await message.answer(message_profile[0], reply_markup=keyboards.get_profile_keyboard(message_profile[1], MIN_WITHDRAWAL_AMOUNT), parse_mode="HTML")

@router.callback_query(F.data == 'profile')
async def profile_callback_handler(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    bot_username = (await callback_query.bot.get_me()).username

    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                profile_data = await get_user_profile(cursor, user_id)
                ref_info = await get_user_referral_info(cursor, user_id)
    except Exception as e:
        logger.error(f"DB error in profile_callback_handler for user {user_id}: {e}", exc_info=True)
        await callback_query.answer("Ошибка загрузки данных", show_alert=True)
        return

    message_profile = get_profile_text(
        user_id=user_id,
        bot_username=bot_username,
        profile_data=profile_data,
        ref_info=ref_info,
        ref_percentage=REFERRAL_PERCENTAGE
    )

    await callback_query.message.answer(
        message_profile[0],
        reply_markup=keyboards.get_profile_keyboard(message_profile[1], MIN_WITHDRAWAL_AMOUNT),
        parse_mode="HTML"
    )
    try:
        await callback_query.message.delete()
    except AiogramError:
        pass
    await callback_query.answer()



# =============================================================================
# --- БЛОК: ПРОМОКОДЫ ---
# =============================================================================

@router.message(Command(commands=['promo']))
@router.callback_query(F.data == 'activate_promo')
async def promo_command_handler(event: Union[Message, CallbackQuery], state: FSMContext):
    """Обработчик команды /promo и кнопки 'Активировать промокод'."""
    await state.set_state(UserPromoStates.waiting_for_code)
    text = "Введите ваш промокод:"
    
    if isinstance(event, Message):
        await event.answer(text)
    else: # CallbackQuery
        await event.message.answer(text)
        await event.answer()

@router.message(UserPromoStates.waiting_for_code)
async def process_user_promo_code(message: Message, state: FSMContext):
    """Ловит ввод промокода от пользователя."""
    code = message.text.strip()
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                result = await activate_promo_for_user(cursor, message.from_user.id, code)
                await db.commit()
    except Exception as e:
        logger.error(f"DB error during promo activation for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.")
        await state.clear()
        return

    if result == "success":
        await message.answer("✅ Промокод успешно активирован! Ваш следующий обмен будет без комиссии.")
    elif result == "invalid_or_expired":
        await message.answer("❌ Такого промокода не существует, он неактивен, или у него закончились использования.")
    elif result == "already_active":
        await message.answer("⚠️ У вас уже есть другой активный промокод. Сначала используйте его.")
    elif result == "already_redeemed":
        await message.answer("⚠️ Вы уже использовали этот промокод ранее.")
    else: # 'error'
        await message.answer("Произошла системная ошибка, попробуйте позже.")
    
    await state.clear()



@router.message(Command(commands=['referral']))
async def referral_handler(message: Message):
    """Показывает реферальное меню пользователя по команде /referral."""
    user_id = message.from_user.id
    bot_username = (await message.bot.get_me()).username

    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                ref_info = await get_user_referral_info(cursor, user_id)
    except Exception as e:
        logger.error(f"DB error in referral_handler for user {user_id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при загрузке ваших данных. Попробуйте позже.")
        return

    text = texts.get_referral_menu_text(bot_username, user_id, ref_info, REFERRAL_PERCENTAGE)
    keyboard = texts.get_referral_menu_keyboard(ref_info.get('balance', 0.0), MIN_WITHDRAWAL_AMOUNT)

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML", disable_web_page_preview=True)


@router.callback_query(F.data == "ref_withdraw")
async def withdrawal_request_handler(callback: CallbackQuery, state: FSMContext):
    """Инициирует процесс вывода реферального баланса по кнопке."""
    user_id = callback.from_user.id
    ref_info = {}
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                ref_info = await get_user_referral_info(cursor, user_id)
    except Exception as e:
        logger.error(f"DB error in withdrawal_request_handler for user {user_id}: {e}", exc_info=True)
        await callback.answer("Ошибка базы данных!", show_alert=True)
        return

    balance = ref_info.get('balance', 0.0)
    if balance < MIN_WITHDRAWAL_AMOUNT:
        await callback.answer(f"Недостаточно средств. Мин. сумма для вывода: {MIN_WITHDRAWAL_AMOUNT} RUB.", show_alert=True)
        return

    await state.update_data(withdrawal_amount=balance)
    await state.set_state(ReferralStates.waiting_for_withdrawal_details)

    text = texts.get_withdrawal_prompt_text(MIN_WITHDRAWAL_AMOUNT, balance)
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.message(ReferralStates.waiting_for_withdrawal_details)
async def process_withdrawal_details_handler(message: Message, state: FSMContext):
    """Обрабатывает введенные реквизиты и создает тикет на вывод."""
    user_id = message.from_user.id
    user_details = message.text.strip()
    fsm_data = await state.get_data()
    amount = fsm_data.get('withdrawal_amount')

    if not amount:
        await message.answer("Произошла ошибка, не найдена сумма вывода. Попробуйте снова.")
        await state.clear()
        return

    try:
        topic = await message.bot.create_forum_topic(
            chat_id=SUPPORT_GROUP_ID,
            name=f"Вывод {amount:,.0f} RUB для {message.from_user.full_name}"
        )

        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                await create_withdrawal_request(cursor, user_id, amount, topic.message_thread_id)
                await db.commit()

        admin_text = texts.get_withdrawal_request_admin_notification(
            user_id, message.from_user.username, amount
        )
        full_admin_text = f"{admin_text}\n\n<b>Реквизиты пользователя:</b>\n<code>{user_details}</code>"

        await message.bot.send_message(
            chat_id=SUPPORT_GROUP_ID,
            message_thread_id=topic.message_thread_id,
            text=full_admin_text,
            parse_mode="HTML"
        )

        await message.answer(
            f"✅ Заявка на вывод <b>{amount:,.2f} RUB</b> создана!\n\n"
            "Оператор свяжется с вами для обработки выплаты. Ваш реферальный баланс был обнулен.",
            parse_mode="HTML"
        )
        logger.info(f"User {user_id} created withdrawal request for {amount:.2f} RUB.")
    except Exception as e:
        logger.error(f"Critical error in withdrawal process for user {user_id}: {e}", exc_info=True)
        await message.answer("❌ Произошла критическая ошибка при создании заявки на вывод. Сообщите оператору.")
    finally:
        await state.clear()

    
    
    
@router.callback_query(F.data == "ref_earnings_history")
async def referral_earnings_handler(callback: CallbackQuery):
    """Показывает пользователю историю его реферальных начислений."""
    user_id = callback.from_user.id
    
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # Получаем и баланс, и историю за одно подключение
                ref_info = await get_user_referral_info(cursor, user_id)
                earnings_history = await get_referral_earnings_history(cursor, user_id)
    except Exception as e:
        logger.error(f"DB error in referral_earnings_handler for user {user_id}: {e}", exc_info=True)
        await callback.answer("Ошибка при загрузке истории. Попробуйте позже.", show_alert=True)
        return

    # Формируем текст сообщения
    text = texts.get_referral_earnings_text(earnings_history, ref_info.get('balance', 0.0))
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = keyboards.get_back_to_main_menu_keyboard()
    
    # Редактируем сообщение, показывая историю
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()
