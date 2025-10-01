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
from handlers import router
from utils.states import TransactionStates
from utils.database.db_connector import init_db
from utils.logging_config import logger

# --- ИЗМЕНЕНИЕ: Импортируем фабрики колбеков и состояния для промокодов ---
from utils.callbacks import CryptoInputSwitch, CryptoSelection, RubInputSwitch
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
        BotCommand(command="/admin", description="Admin panel"),
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

    # Регистрация роутеров — handlers/router.py создаёт Router'ы
    dp.include_router(router.main_router)
    dp.include_router(router.crypto_router)
    dp.include_router(router.admin_router)
    # Include proxy routers if available
    dp.include_router(router.private_message_router)
    dp.include_router(router.group_message_router) # <-- Вот он, ключ к решению проблемы!


    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())