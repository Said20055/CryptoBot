import aiosqlite
from typing import Optional
from utils.logging_config import logger
from utils.database.db_connector import DB_NAME
from utils.database import db_queries


async def get_active_order_for_user(user_id: int) -> Optional[dict]:
    """Обертывает db_queries.get_active_order_for_user, управляя соединением.

    Возвращает dict с данными заявки или None. Логирует и возвращает None при ошибке.
    """
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                return await db_queries.get_active_order_for_user(cursor, user_id)
    except Exception as e:
        logger.error(f"DB helper error in get_active_order_for_user for {user_id}: {e}", exc_info=True)
        return None


async def get_order_by_topic_id(topic_id: int) -> Optional[dict]:
    """Обертывает db_queries.get_order_by_topic_id, управляя соединением.

    Возвращает dict с полями order_id и user_id или None.
    """
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                return await db_queries.get_order_by_topic_id(cursor, topic_id)
    except Exception as e:
        logger.error(f"DB helper error in get_order_by_topic_id for topic {topic_id}: {e}", exc_info=True)
        return None
