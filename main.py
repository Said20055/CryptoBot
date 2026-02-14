"""
Главный модуль Telegram бота для обмена криптовалют.
"""
import asyncio
import random
import aiosqlite
from aiogram import Bot, Dispatcher, F

import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.exceptions import AiogramError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat

from config import (
    TOKEN, ADMIN_CHAT_ID, SUPPORT_GROUP_ID, ORDER_AUTO_CLOSE_MINUTES,
    ADMIN_REMINDER_MIN_SECONDS, ADMIN_REMINDER_MAX_SECONDS
)
from handlers import main as main_handlers, crypto, admin
from handlers import router
from handlers.lottery import lottery_router
from utils.states import TransactionStates
from utils.database.db_connector import init_db, DB_NAME
from utils.logging_config import logger

# --- ИЗМЕНЕНИЕ: Импортируем фабрики колбеков и состояния для промокодов ---
from utils.callbacks import CryptoInputSwitch, CryptoSelection, RubInputSwitch
from handlers.main import UserPromoStates
from utils.database.db_queries import get_stale_processing_orders, get_processing_orders, update_order_status


async def auto_close_orders_loop(bot: Bot):
    """Периодически автозакрывает заявки старше ORDER_AUTO_CLOSE_MINUTES."""
    while True:
        try:
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.cursor() as cursor:
                    stale_orders = await get_stale_processing_orders(cursor, ORDER_AUTO_CLOSE_MINUTES)
                    for order in stale_orders:
                        changed = await update_order_status(cursor, order['order_id'], 'auto_closed')
                        if not changed:
                            continue

                        order_number = order['order_id'] + 9999
                        user_id = order['user_id']
                        topic_id = order['topic_id']

                        try:
                            await bot.send_message(
                                chat_id=user_id,
                                text=(
                                    f"⏱ Заявка <b>#{order_number}</b> автоматически закрыта, "
                                    f"так как не была обработана в течение {ORDER_AUTO_CLOSE_MINUTES} минут."
                                ),
                                parse_mode='HTML'
                            )
                        except Exception as e:
                            logger.warning(f"Could not notify user {user_id} about auto close: {e}")

                        if topic_id:
                            try:
                                await bot.send_message(
                                    chat_id=SUPPORT_GROUP_ID,
                                    message_thread_id=topic_id,
                                    text=(
                                        f"⏱ <b>Заявка #{order_number} автоматически закрыта</b> "
                                        f"(превышено время ожидания {ORDER_AUTO_CLOSE_MINUTES} мин)."
                                    ),
                                    parse_mode='HTML'
                                )
                            except Exception as e:
                                logger.warning(f"Could not notify topic {topic_id} about auto close: {e}")

                    if stale_orders:
                        await db.commit()
        except Exception as e:
            logger.error(f"auto_close_orders_loop error: {e}", exc_info=True)

        await asyncio.sleep(60)


async def admin_orders_reminder_loop(bot: Bot):
    """Периодически напоминает админам о необработанных заявках раз в 2-3 минуты."""
    while True:
        try:
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.cursor() as cursor:
                    processing_orders = await get_processing_orders(cursor)

            if processing_orders:
                preview = ', '.join(f"#{o['order_id'] + 9999}" for o in processing_orders[:5])
                suffix = ' ...' if len(processing_orders) > 5 else ''
                for admin_id in ADMIN_CHAT_ID:
                    if(admin_id!=ADMIN_CHAT_ID[0]):
                        await bot.send_message(
                            chat_id=admin_id,
                            text=(
                                f"🔔 Напоминание: в работе <b>{len(processing_orders)}</b> заявок. "
                                f"Проверьте, пожалуйста: {preview}{suffix}"
                            ),
                            parse_mode='HTML'
                        )
        except Exception as e:
            logger.error(f"admin_orders_reminder_loop error: {e}", exc_info=True)

        await asyncio.sleep(random.randint(ADMIN_REMINDER_MIN_SECONDS, ADMIN_REMINDER_MAX_SECONDS))


async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    bot_info = await bot.get_me()
    logger.info(f"Bot started: {bot_info.first_name} @{bot_info.username}")

    dp = Dispatcher(storage=MemoryStorage())

    default_commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/profile", description="Показать мой профиль"),
        BotCommand(command="/promo", description="Активировать промокод"),
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

    dp.include_router(router.main_router)
    dp.include_router(lottery_router)
    dp.include_router(router.crypto_router)
    dp.include_router(router.admin_router)
    dp.include_router(router.private_message_router)
    dp.include_router(router.group_message_router)

    auto_close_task = asyncio.create_task(auto_close_orders_loop(bot))
    admin_reminder_task = asyncio.create_task(admin_orders_reminder_loop(bot))

    auto_close_task = asyncio.create_task(auto_close_orders_loop(bot))
    admin_reminder_task = asyncio.create_task(admin_orders_reminder_loop(bot))

    try:
        await dp.start_polling(bot)
    finally:
        auto_close_task.cancel()
        admin_reminder_task.cancel()
        await asyncio.gather(auto_close_task, admin_reminder_task, return_exceptions=True)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
