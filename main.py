"""
Главный модуль Telegram бота для обмена криптовалют
"""
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import BotCommandScopeChat, BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import AiogramError

from config import TOKEN, ADMIN_CHAT_ID
from handlers import main as main_handlers, crypto, admin
from utils.states import TransactionStates
from utils.database.db_connector import init_db
from utils.logging_config import logger

# --- ИЗМЕНЕНИЕ: Импортируем фабрики колбеков и состояния для промокодов ---
from utils.callbacks import CryptoInputSwitch, CryptoSelection, RubInputSwitch
from handlers.admin import PromoStates
from handlers.main import UserPromoStates


async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    bot_info = await bot.get_me()
    logger.info(f"Bot started: {bot_info.first_name} @{bot_info.username}")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация команд для меню бота
    default_commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/profile", description="Показать мой профиль"),
        BotCommand(command="/promo", description="Активировать промокод"),
        BotCommand(command="/help", description="Получить справку"),
        BotCommand(command="/id", description="Получить ваш Telegram ID")
    ]
    admin_commands = default_commands + [
        BotCommand(command="/users", description="Получить список пользователей"),
        BotCommand(command="/log", description="Получить файл логов бота"),
        BotCommand(command="/send", description="Рассылка сообщений"),
        BotCommand(command="/addpromo", description="Создать промокод")
    ]

    await bot.set_my_commands(default_commands)
    for admin_id in ADMIN_CHAT_ID:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
            logger.info(f"Admin commands successfully set for admin_id: {admin_id}")
        except AiogramError as e:
            logger.error(f"Failed to set admin commands for admin_id: {admin_id}. Error: {e}")
            logger.warning(f"Possible reason: Admin {admin_id} has not started the bot yet.")
        except Exception as e:
            logger.error(f"An unexpected error occurred while setting commands for {admin_id}: {e}")

    # --- РЕГИСТРАЦИЯ ХЕНДЛЕРОВ СООБЩЕНИЙ ---

    # Команды
    dp.message.register(main_handlers.start_handler, Command(commands=['start']))
    dp.message.register(main_handlers.help_handler, Command(commands=['help']))
    dp.message.register(main_handlers.id_handler, Command(commands=['id']))
    dp.message.register(main_handlers.profile_handler, Command(commands=['profile']))
    dp.message.register(main_handlers.promo_command_handler, Command(commands=['promo']))
    
    # Админские команды
    dp.message.register(admin.users_handler, Command(commands=['users']))
    dp.message.register(admin.log_handler, Command(commands=["log"]))
    dp.message.register(admin.send_handler, Command(commands=["send"]))
    dp.message.register(admin.add_promo_handler, Command(commands=['addpromo']))

    # Другие типы сообщений
    dp.message.register(main_handlers.image_handler, F.photo)

    # --- РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ДЛЯ СОСТОЯНИЙ (FSM) ---

    # Состояния для рассылки (админ)
    dp.message.register(admin.broadcast_message_handler, admin.BroadcastStates.waiting_for_message)

    # Состояния для ответа админа пользователю
    class AdminReplyStates(StatesGroup):
        waiting_for_reply_message = State()
    dp.message.register(admin.admin_reply_message_handler, AdminReplyStates.waiting_for_reply_message)

    # --- ИЗМЕНЕНИЕ: Регистрация универсального хендлера для ввода суммы ---
    dp.message.register(crypto.process_amount_input, TransactionStates.waiting_for_crypto_amount)
    dp.message.register(crypto.process_amount_input, TransactionStates.waiting_for_rub_amount)
    
    # Остальные состояния транзакций
    dp.message.register(crypto.phone_input_handler, TransactionStates.waiting_for_phone)
    dp.message.register(crypto.tx_link_input_handler, TransactionStates.waiting_for_tx_link)
    dp.message.register(crypto.operator_reply_input_handler, TransactionStates.waiting_for_operator_reply)
    
    # Состояния для промокодов
    dp.message.register(admin.process_new_promo_code, PromoStates.waiting_for_promo_code)
    dp.message.register(main_handlers.process_user_promo_code, UserPromoStates.waiting_for_code)


    # --- РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ДЛЯ НАЖАТИЙ НА КНОПКИ (CALLBACK) ---

    # Главное меню и профиль
    dp.callback_query.register(main_handlers.start_handler, F.data == 'main_menu')
    dp.callback_query.register(main_handlers.profile_handler, F.data == 'profile')

    # Выбор действия (продать/купить)
    dp.callback_query.register(crypto.sell_handler, F.data == 'sell')
    dp.callback_query.register(crypto.buy_handler, F.data == 'buy')

   
    dp.callback_query.register(crypto.cancel_order_handler, F.data.startswith('cancel_order_'))
    
    dp.callback_query.register(main_handlers.promo_command_handler, F.data == 'activate_promo')
    # --- ИЗМЕНЕНИЕ: УДАЛЕНЫ 24 СТАРЫХ ОБРАБОТЧИКА, ДОБАВЛЕНЫ 2 НОВЫХ ---
    # Универсальный хендлер для выбора криптовалюты (ловит все колбеки типа "crypto_select:...")
    dp.callback_query.register(crypto.select_crypto_handler, CryptoSelection.filter())
    # Универсальный хендлер для переключения на ввод в рублях (ловит все колбеки типа "rub_switch:...")
    dp.callback_query.register(crypto.switch_to_rub_input_handler, RubInputSwitch.filter())

    dp.callback_query.register(crypto.select_crypto_handler, CryptoInputSwitch.filter())
    # Админские колбеки
    dp.callback_query.register(admin.cancel_broadcast_handler, F.data == 'cancel_broadcast')
    dp.callback_query.register(admin.admin_reply_handler, F.data.startswith('admin_reply_'))
    # Здесь можно добавить регистрацию для подтверждения/отмены заказа админом
    
    dp.callback_query.register(admin.confirm_order_handler, F.data.startswith('confirm_order_'))
    dp.callback_query.register(admin.reject_order_handler, F.data.startswith('reject_order_'))
    # dp.callback_query.register(admin.confirm_order_handler, F.data.startswith('confirm_order_'))

    # Колбеки транзакций
    dp.callback_query.register(crypto.payment_sbp_handler, F.data == 'payment_sbp')
    dp.callback_query.register(crypto.payment_operator_handler, F.data == 'payment_operator')
    dp.callback_query.register(crypto.cancel_transaction_handler, F.data == 'cancel_transaction')
    dp.callback_query.register(crypto.cancel_order_handler, F.data == 'cancel_order')
    dp.callback_query.register(crypto.send_tx_link_handler, F.data == 'send_tx_link')
    dp.callback_query.register(crypto.reply_to_operator_handler, F.data == 'reply_to_operator')


    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())