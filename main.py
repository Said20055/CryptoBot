"""
Главный модуль Telegram бота для обмена криптовалют
"""
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import BotCommandScopeChat, BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from config import TOKEN, ADMIN_CHAT_ID
from handlers import main as main_handlers, crypto, admin
from utils.states import TransactionStates
from utils.database import init_sqlite
from utils.logging_config import logger



# Вспомогательные корутины для передачи dp и state в обработчики подписок



async def main():
    await init_sqlite()
    bot = Bot(token=TOKEN)
    bot_info = await bot.get_me()
    logger.info(f"Bot started: {bot_info.first_name} @{bot_info.username}")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация команд для меню бота
    default_commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/help", description="Получить справку"),
        BotCommand(command="/id", description="Получить ваш Telegram ID")
    ]
    admin_commands = default_commands + [
        BotCommand(command="/users", description="Получить список пользователей"),
        BotCommand(command="/log", description="Получить файл логов бота"),
        BotCommand(command="/send", description="Рассылка сообщений"),
    ]
    
    await bot.set_my_commands(default_commands)
    for admin_id in ADMIN_CHAT_ID:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to set admin commands for {admin_id}: {e}")
    
    # Регистрация хэндлеров
    dp.message.register(main_handlers.start_handler, Command(commands=['start']))
    dp.message.register(main_handlers.help_handler, Command(commands=['help']))
    dp.message.register(main_handlers.id_handler, Command(commands=['id']))
    dp.message.register(admin.users_handler, Command(commands=['users']))
    dp.message.register(admin.log_handler, Command(commands=["log"]))
    dp.message.register(admin.send_handler, Command(commands=["send"]))
    #dp.message.register(chat_id_handler, F.chat.type.in_({"group", "supergroup", "channel"}))
    dp.message.register(main_handlers.image_handler, F.photo)
    
    # Регистрация хендлеров для рассылки
    dp.message.register(admin.broadcast_message_handler, admin.BroadcastStates.waiting_for_message)
    
    # Регистрация хендлеров для ответа админа пользователю
    class AdminReplyStates(StatesGroup):
        waiting_for_reply_message = State()
    dp.message.register(admin.admin_reply_message_handler, AdminReplyStates.waiting_for_reply_message)
    
    # Регистрация хендлеров для ввода суммы
    dp.message.register(crypto.handle_crypto_amount_input, TransactionStates.waiting_for_crypto_amount)
    dp.message.register(crypto.handle_rub_amount_input, TransactionStates.waiting_for_rub_amount)
    dp.message.register(crypto.phone_input_handler, TransactionStates.waiting_for_phone)
    dp.message.register(crypto.tx_link_input_handler, TransactionStates.waiting_for_tx_link)
    dp.message.register(crypto.operator_reply_input_handler, TransactionStates.waiting_for_operator_reply)


    # Callback handlers
    dp.callback_query.register(main_handlers.start_handler, F.data == 'main_menu')
    
    # Crypto exchange callbacks
    dp.callback_query.register(crypto.sell_handler, F.data == 'sell')
    dp.callback_query.register(crypto.buy_handler, F.data == 'buy')
    
    # Sell crypto callbacks
    dp.callback_query.register(crypto.sell_btc_handler, F.data == 'sell_btc')
    dp.callback_query.register(crypto.sell_ltc_handler, F.data == 'sell_ltc')
    dp.callback_query.register(crypto.sell_trx_handler, F.data == 'sell_trx')
    dp.callback_query.register(crypto.sell_usdt_handler, F.data == 'sell_usdt')
    
    # Buy crypto callbacks
    dp.callback_query.register(crypto.buy_btc_handler, F.data == 'buy_btc')
    dp.callback_query.register(crypto.buy_ltc_handler, F.data == 'buy_ltc')
    dp.callback_query.register(crypto.buy_trx_handler, F.data == 'buy_trx')
    dp.callback_query.register(crypto.buy_usdt_handler, F.data == 'buy_usdt')
    
    # Sell crypto rub callbacks
    dp.callback_query.register(crypto.sell_btc_rub_handler, F.data == 'sell_btc_rub')
    dp.callback_query.register(crypto.sell_ltc_rub_handler, F.data == 'sell_ltc_rub')
    dp.callback_query.register(crypto.sell_trx_rub_handler, F.data == 'sell_trx_rub')
    dp.callback_query.register(crypto.sell_usdt_rub_handler, F.data == 'sell_usdt_rub')
    
    # Buy crypto rub callbacks
    dp.callback_query.register(crypto.buy_btc_rub_handler, F.data == 'buy_btc_rub')
    dp.callback_query.register(crypto.buy_ltc_rub_handler, F.data == 'buy_ltc_rub')
    dp.callback_query.register(crypto.buy_trx_rub_handler, F.data == 'buy_trx_rub')
    dp.callback_query.register(crypto.buy_usdt_rub_handler, F.data == 'buy_usdt_rub')
    
    # Admin callbacks
    dp.callback_query.register(admin.cancel_broadcast_handler, F.data == 'cancel_broadcast')
    dp.callback_query.register(admin.admin_reply_handler, F.data.startswith('admin_reply_'))
    
    # Transaction callbacks
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