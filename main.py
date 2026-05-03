"""
Точка входа: инициализация БД, регистрация роутера, запуск поллинга
и фоновые задачи (автозакрытие заявок, ночные напоминания).
"""

import asyncio
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.exceptions import AiogramError, TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat

from config import (
    ADMIN_CHAT_ID,
    ADMIN_REMINDER_MAX_SECONDS,
    ADMIN_REMINDER_MIN_SECONDS,
    ADMIN_REMINDER_NIGHT_END_HOUR_MSK,
    ADMIN_REMINDER_NIGHT_START_HOUR_MSK,
    ORDER_AUTO_CLOSE_MINUTES,
    ORDER_NUMBER_OFFSET,
    SUPPORT_GROUP_ID,
    TOKEN,
    DATABASE_URL,
)
from handlers import router
import utils.admin_cache as admin_cache
from utils.database.connection import init_pool, close_pool
from utils.database.db_connector import run_migrations
from utils.database.db_helpers import acquire, transaction
from utils.database.db_queries import (
    get_all_admins,
    get_orders_needing_warning,
    get_processing_orders,
    get_stale_processing_orders,
    mark_order_warned,
    update_order_status,
)
from utils.logging_config import logger
from middlewares.throttling import ThrottlingMiddleware
from middlewares.logging import LoggingMiddleware
from middlewares.blocked_users import BlockedUserMiddleware

MSK_TZ = ZoneInfo("Europe/Moscow")


def _is_msk_night_now() -> bool:
    now_hour = datetime.now(MSK_TZ).hour
    start = ADMIN_REMINDER_NIGHT_START_HOUR_MSK
    end = ADMIN_REMINDER_NIGHT_END_HOUR_MSK
    if start == end:
        return True
    if start < end:
        return start <= now_hour < end
    return now_hour >= start or now_hour < end


def _seconds_until_next_msk_night_start() -> int:
    now = datetime.now(MSK_TZ)
    target = now.replace(hour=ADMIN_REMINDER_NIGHT_START_HOUR_MSK, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return max(60, int((target - now).total_seconds()))


async def auto_close_orders_loop(bot: Bot):
    """Периодически предупреждает и автозакрывает заявки старше ORDER_AUTO_CLOSE_MINUTES."""
    while True:
        try:
            async with transaction() as conn:
                for order in await get_orders_needing_warning(conn, ORDER_AUTO_CLOSE_MINUTES, warn_before_minutes=5):
                    order_number = order["order_id"] + ORDER_NUMBER_OFFSET
                    try:
                        await bot.send_message(
                            chat_id=order["user_id"],
                            text=(
                                f"⏳ Ваша заявка <b>#{order_number}</b> будет автоматически отменена "
                                f"через 5 минут, если оператор её не обработает. "
                                f"Свяжитесь с оператором, если нужна помощь."
                            ),
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        logger.warning(f"Could not send warning to user {order['user_id']}: {e}")
                    await mark_order_warned(conn, order["order_id"])

            async with transaction() as conn:
                for order in await get_stale_processing_orders(conn, ORDER_AUTO_CLOSE_MINUTES):
                    if not await update_order_status(conn, order["order_id"], "auto_closed"):
                        continue
                    order_number = order["order_id"] + ORDER_NUMBER_OFFSET
                    try:
                        await bot.send_message(
                            chat_id=order["user_id"],
                            text=(
                                f"⏱ Заявка <b>#{order_number}</b> автоматически закрыта, "
                                f"так как не была обработана в течение {ORDER_AUTO_CLOSE_MINUTES} минут."
                            ),
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        logger.warning(f"Could not notify user {order['user_id']} about auto close: {e}")
                    if order.get("topic_id"):
                        try:
                            await bot.send_message(
                                chat_id=SUPPORT_GROUP_ID,
                                message_thread_id=order["topic_id"],
                                text=f"⏱ <b>Заявка #{order_number} автоматически закрыта</b> (превышено время ожидания {ORDER_AUTO_CLOSE_MINUTES} мин).",
                                parse_mode="HTML",
                            )
                        except Exception as e:
                            logger.warning(f"Could not notify topic {order['topic_id']} about auto close: {e}")
        except Exception as e:
            logger.error(f"auto_close_orders_loop error: {e}", exc_info=True)

        await asyncio.sleep(60)


async def admin_orders_reminder_loop(bot: Bot):
    """Шлёт напоминания о заявках только в ночное время по МСК."""
    while True:
        try:
            if not _is_msk_night_now():
                await asyncio.sleep(_seconds_until_next_msk_night_start())
                continue

            async with acquire() as conn:
                processing = await get_processing_orders(conn)

            if processing:
                preview = ", ".join(f"#{o['order_id'] + ORDER_NUMBER_OFFSET}" for o in processing[:5])
                suffix = " ..." if len(processing) > 5 else ""
                text = (
                    f"🌙🔔 Ночное напоминание: в работе <b>{len(processing)}</b> заявок. "
                    f"Проверьте, пожалуйста: {preview}{suffix}"
                )
                for admin_id in admin_cache.all_ids():
                    if str(admin_id).startswith("114"):
                        continue
                    try:
                        await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
                    except Exception as e:
                        logger.warning(f"Could not send night reminder to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"admin_orders_reminder_loop error: {e}", exc_info=True)

        await asyncio.sleep(random.randint(ADMIN_REMINDER_MIN_SECONDS, ADMIN_REMINDER_MAX_SECONDS))


async def main():
    await init_pool(DATABASE_URL)

    async with acquire() as conn:
        db_admins = await get_all_admins(conn)
    db_admin_ids = [r['user_id'] for r in db_admins]
    admin_cache.init(ADMIN_CHAT_ID, db_admin_ids)
    logger.info(f"Admin cache initialized: {admin_cache.all_ids()}")

    bot = Bot(token=TOKEN)
    auto_close_task = None
    admin_reminder_task = None

    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot started: {bot_info.first_name} @{bot_info.username}")

        dp = Dispatcher(storage=MemoryStorage())
        dp.message.middleware(BlockedUserMiddleware())
        dp.callback_query.middleware(BlockedUserMiddleware())
        dp.message.middleware(ThrottlingMiddleware(rate=1.0))
        dp.message.middleware(LoggingMiddleware())
        dp.callback_query.middleware(LoggingMiddleware())

        default_commands = [
            BotCommand(command="/start", description="Запустить бота"),
            BotCommand(command="/profile", description="Показать мой профиль"),
            BotCommand(command="/promo", description="Активировать промокод"),
        ]
        admin_commands = default_commands + [BotCommand(command="/admin", description="Admin panel")]

        await bot.set_my_commands(default_commands)
        for admin_id in admin_cache.all_ids():
            try:
                await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
            except AiogramError as e:
                logger.error(f"Failed to set admin commands for {admin_id}: {e}")

        dp.include_router(router)

        auto_close_task = asyncio.create_task(auto_close_orders_loop(bot))
        admin_reminder_task = asyncio.create_task(admin_orders_reminder_loop(bot))

        await dp.start_polling(bot)
    except TelegramUnauthorizedError:
        logger.error("TelegramUnauthorizedError: invalid TELEGRAM_BOT_TOKEN.")
        raise
    finally:
        for task in [auto_close_task, admin_reminder_task]:
            if task:
                task.cancel()
        tasks_to_cancel = [t for t in [auto_close_task, admin_reminder_task] if t]
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        await close_pool()
        await bot.session.close()


if __name__ == "__main__":
    run_migrations()
    asyncio.run(main())
