# utils/db_queries.py

"""
Модуль, содержащий все функции для выполнения запросов к базе данных.
Функции здесь НЕ управляют соединением, а принимают готовый курсор.
"""
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import aiosqlite
from utils.logging_config import logger

# --- USER QUERIES ---

async def save_or_update_user(cursor: aiosqlite.Cursor, user_id: int, username: str, full_name: str) -> bool:
    """Сохраняет или обновляет данные пользователя, используя переданный курсор."""
    await cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    is_new_user = await cursor.fetchone() is None

    if is_new_user:
        await cursor.execute(
            "INSERT INTO users (user_id, username, full_name, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, datetime.now())
        )
    else:
        await cursor.execute(
            "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
            (username, full_name, user_id)
        )
    logger.info(f"User {user_id} {'saved' if is_new_user else 'updated'} in DB.")
    return is_new_user

async def find_all_users(cursor: aiosqlite.Cursor) -> List[tuple]:
    """Получает список всех пользователей."""
    await cursor.execute("SELECT user_id, username, full_name FROM users")
    return await cursor.fetchall()

async def get_user_profile(cursor: aiosqlite.Cursor, user_id: int) -> Optional[Dict[str, Any]]:
    """Получает профиль пользователя, считая только УСПЕШНЫЕ сделки."""
    await cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
    user_data = await cursor.fetchone()
    if not user_data:
        return None

    await cursor.execute(
        "SELECT COUNT(order_id), COALESCE(SUM(amount_rub), 0) FROM orders WHERE user_id = ? AND status = 'completed'",
        (user_id,)
    )
    stats_data = await cursor.fetchone()
    
    return {
        'user_id': user_id,
        'username': user_data[0],
        'total_orders': stats_data[0],
        'total_volume_rub': stats_data[1]
    }

# --- ORDER QUERIES ---

async def create_order(cursor: aiosqlite.Cursor, user_id: int, username: str, action: str, 
                      crypto: str, amount_crypto: float, amount_rub: float, 
                      phone_and_bank: str, promo_code: Optional[str],
                      topic_id: int) -> int:
    """Создает новую заявку, сохраняя ID темы, и возвращает ее ID."""
    await cursor.execute('''
        INSERT INTO orders (user_id, topic_id, username, action, crypto, 
                          amount_crypto, amount_rub, phone_and_bank, created_at, promo_code_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, topic_id, username, action, crypto, amount_crypto, amount_rub, 
          phone_and_bank, datetime.now(), promo_code))
    order_id = cursor.lastrowid
    logger.info(f"Created order #{order_id} in topic #{topic_id} for user {user_id}. Promo: {promo_code}")
    return order_id

async def update_order_status(cursor: aiosqlite.Cursor, order_id: int, new_status: str) -> bool:
    """Обновляет статус указанной заявки."""
    allowed_statuses = ['processing', 'completed', 'rejected', 'cancelled_by_user']
    if new_status not in allowed_statuses:
        logger.error(f"Attempted to set an invalid order status: {new_status}")
        return False
        
    await cursor.execute(
        "UPDATE orders SET status = ? WHERE order_id = ?",
        (new_status, order_id)
    )
    return cursor.rowcount > 0

async def get_order_status(cursor: aiosqlite.Cursor, order_id: int) -> Optional[str]:
    """Возвращает текущий статус заявки."""
    await cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,))
    result = await cursor.fetchone()
    return result[0] if result else None

# --- НОВАЯ ФУНКЦИЯ: Поиск активной заявки для защиты от спама ---
async def get_active_order_for_user(cursor: aiosqlite.Cursor, user_id: int) -> Optional[dict]:
    """Ищет активную (в обработке) заявку для пользователя и возвращает ее детали (С ЛОГИРОВАНИЕМ)."""
    logger.info(f"DB Query: Searching for active order with status 'processing' for user_id={user_id}")
    await cursor.execute(
        """
        SELECT order_id, topic_id, action, crypto, amount_crypto, amount_rub, phone_and_bank
        FROM orders 
        WHERE user_id = ? AND status = 'processing'
        """,
        (user_id,)
    )
    row = await cursor.fetchone()
    if row:
        result = {
            'order_id': row[0], 'topic_id': row[1], 'action': row[2],
            'crypto': row[3], 'amount_crypto': row[4], 'total_amount': row[5],
            'user_input': row[6]
        }
        logger.info(f"DB Query: Found active order for user_id={user_id}. Data: {result}")
        return result
    
    logger.info(f"DB Query: No active order found for user_id={user_id}.")
    return None

# --- НОВАЯ ФУНКЦИЯ: Поиск заявки по ID темы для команд в группе ---
async def get_order_by_topic_id(cursor: aiosqlite.Cursor, topic_id: int) -> Optional[dict]:
    """Ищет заявку по ID ее темы в Telegram."""
    await cursor.execute(
        "SELECT order_id, user_id FROM orders WHERE topic_id = ?",
        (topic_id,)
    )
    row = await cursor.fetchone()
    if row:
        return {'order_id': row[0], 'user_id': row[1]}
    return None
# --- PROMO CODE QUERIES ---

async def add_promo_code(cursor: aiosqlite.Cursor, code: str, total_uses: int) -> bool:
    """Добавляет новый промокод."""
    try:
        await cursor.execute(
            "INSERT INTO promo_codes (code, total_uses, uses_left, created_at) VALUES (?, ?, ?, ?)",
            (code.upper(), total_uses, total_uses, datetime.now())
        )
        return True
    except aiosqlite.IntegrityError:
        return False

async def activate_promo_for_user(cursor: aiosqlite.Cursor, user_id: int, code: str) -> str:
    """Активирует промокод для пользователя."""
    code = code.upper()
    await cursor.execute("SELECT 1 FROM used_promo_codes WHERE user_id = ? AND promo_code = ?", (user_id, code))
    if await cursor.fetchone():
        return "already_redeemed"

    await cursor.execute("SELECT activated_promo FROM users WHERE user_id = ?", (user_id,))
    result = await cursor.fetchone()
    if result and result[0]:
        return "already_active"

    await cursor.execute("SELECT uses_left, is_active FROM promo_codes WHERE code = ?", (code,))
    promo = await cursor.fetchone()
    if not promo or not promo[1] or promo[0] < 1:
        return "invalid_or_expired"

    await cursor.execute("UPDATE users SET activated_promo = ? WHERE user_id = ?", (code, user_id))
    return "success"

async def get_user_activated_promo(cursor: aiosqlite.Cursor, user_id: int) -> Optional[str]:
    """Возвращает активный промокод пользователя."""
    await cursor.execute("SELECT activated_promo FROM users WHERE user_id = ?", (user_id,))
    result = await cursor.fetchone()
    return result[0] if result and result[0] else None

async def clear_user_activated_promo(cursor: aiosqlite.Cursor, user_id: int):
    """Очищает активный промокод пользователя."""
    await cursor.execute("UPDATE users SET activated_promo = NULL WHERE user_id = ?", (user_id,))

async def use_activated_promo(cursor: aiosqlite.Cursor, user_id: int, order_id: int) -> bool:
    """'Сжигает' промокод, привязанный к заявке."""
    await cursor.execute("SELECT promo_code_used FROM orders WHERE order_id = ?", (order_id,))
    order_promo_result = await cursor.fetchone()

    if not order_promo_result or not order_promo_result[0]:
        return False

    promo_code = order_promo_result[0]
    await cursor.execute("UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code = ?", (promo_code,))
    # Важно: промокод у юзера мы уже очистили при создании заявки, здесь это делать не нужно.
    await cursor.execute(
        "INSERT INTO used_promo_codes (user_id, promo_code, order_id, used_at) VALUES (?, ?, ?, ?)",
        (user_id, promo_code, order_id, datetime.now())
    )
    return True

async def refund_promo_if_needed(cursor: aiosqlite.Cursor, user_id: int, order_id: int):
    """'Возвращает' промокод пользователю, если заявка отменена."""
    await cursor.execute("SELECT promo_code_used FROM orders WHERE order_id = ?", (order_id,))
    order_promo_result = await cursor.fetchone()

    if not order_promo_result or not order_promo_result[0]:
        return

    promo_to_refund = order_promo_result[0]
    await cursor.execute("DELETE FROM used_promo_codes WHERE user_id = ? AND promo_code = ? AND order_id = ?",
                         (user_id, promo_to_refund, order_id))

    await cursor.execute("SELECT activated_promo FROM users WHERE user_id = ?", (user_id,))
    user_promo = await cursor.fetchone()
    if user_promo and user_promo[0]:
        logger.warning(f"Not refunding '{promo_to_refund}' because user {user_id} has another active promo.")
        return

    await cursor.execute("UPDATE users SET activated_promo = ? WHERE user_id = ?", (promo_to_refund, user_id))
    logger.info(f"Refunded promo '{promo_to_refund}' to user {user_id} for rejected order #{order_id}.")