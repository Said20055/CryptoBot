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

async def save_or_update_user(cursor: aiosqlite.Cursor, user_id: int, username: str, 
                              full_name: str, referrer_id: Optional[int] = None) -> bool:
    """Сохраняет нового пользователя (с реферером) или обновляет существующего."""
    await cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    is_new_user = await cursor.fetchone() is None

    if is_new_user:
        # Если пользователь новый и пришел по реф. ссылке, записываем реферера
        await cursor.execute(
            "INSERT INTO users (user_id, username, full_name, created_at, referrer_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, full_name, datetime.now(), referrer_id)
        )
    else:
        # Для существующих пользователей просто обновляем данные
        await cursor.execute(
            "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
            (username, full_name, user_id)
        )
    logger.info(f"User {user_id} {'saved' if is_new_user else 'updated'}. Referrer ID: {referrer_id if is_new_user else 'N/A'}.")
    return is_new_user


async def find_all_users(cursor):
    """(ИЗМЕНЕНО) Возвращает ID всех пользователей, используя переданный курсор."""
    await cursor.execute("SELECT user_id FROM users")
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

async def get_order_by_id(cursor, order_id: int):
    """Возвращает полную информацию о заявке по ее ID."""
    await cursor.execute("""
        SELECT topic_id, status, amount_rub FROM orders WHERE order_id = ?
    """, (order_id,))
    result = await cursor.fetchone()
    if result:
        # Возвращаем в виде словаря для удобного доступа
        logger.info(f"Refunded promo {result}")
        return {'topic_id': result[0], 'status': result[1], 'amount_rub': result[2]}
    return None

async def get_all_settings(cursor) -> dict:
    """Возвращает все настройки из БД в виде словаря."""
    await cursor.execute("SELECT key, value FROM settings")
    rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}

async def update_setting(cursor, key: str, value: str):
    """Обновляет или вставляет настройку (UPSERT)."""
    await cursor.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = ?
    """, (key, value, value))
    
    

async def get_user_referral_info(cursor: aiosqlite.Cursor, user_id: int) -> dict:
    """Получает полную реферальную информацию о пользователе."""
    # Получаем баланс и ID реферера
    await cursor.execute("SELECT referral_balance, referrer_id FROM users WHERE user_id = ?", (user_id,))
    user_data = await cursor.fetchone() or (0.0, None)
    
    # Считаем количество приглашенных им рефералов
    await cursor.execute("SELECT COUNT(user_id) FROM users WHERE referrer_id = ?", (user_id,))
    referral_count = (await cursor.fetchone())[0]
    
    return {
        'balance': user_data[0],
        'referrer_id': user_data[1],
        'referral_count': referral_count
    }

async def add_referral_earning(cursor: aiosqlite.Cursor, order_id: int, referral_id: int, 
                               order_amount: float, percentage: float) -> bool:
    """Находит реферера, начисляет ему процент и записывает в историю."""
    # 1. Находим, кто пригласил пользователя, совершившего сделку
    await cursor.execute("SELECT referrer_id FROM users WHERE user_id = ?", (referral_id,))
    result = await cursor.fetchone()
    if not result or not result[0]:
        return False # У этого пользователя нет реферера

    referrer_id = result[0]
    
    # 2. Рассчитываем вознаграждение
    earning_amount = order_amount * (percentage / 100.0)
    
    # 3. Обновляем баланс реферера
    await cursor.execute(
        "UPDATE users SET referral_balance = referral_balance + ? WHERE user_id = ?",
        (earning_amount, referrer_id)
    )
    
    # 4. Записываем транзакцию в историю
    await cursor.execute(
        """INSERT INTO referral_earnings 
           (referrer_id, referral_id, order_id, amount, created_at) 
           VALUES (?, ?, ?, ?, ?)""",
        (referrer_id, referral_id, order_id, earning_amount, datetime.now())
    )
    logger.info(f"User {referrer_id} earned {earning_amount:.2f} RUB from referral {referral_id}'s order #{order_id}.")
    return True

async def create_withdrawal_request(cursor: aiosqlite.Cursor, user_id: int, amount: float, topic_id: int) -> bool:
    """Создает заявку на вывод и обнуляет баланс пользователя."""
    await cursor.execute("UPDATE users SET referral_balance = 0.0 WHERE user_id = ?", (user_id,))
    if cursor.rowcount == 0:
        return False # Пользователь не найден

    await cursor.execute(
        "INSERT INTO withdrawal_requests (user_id, amount, created_at, topic_id) VALUES (?, ?, ?, ?)",
        (user_id, amount, datetime.now(), topic_id)
    )
    logger.info(f"User {user_id} created a withdrawal request for {amount:.2f} RUB in topic #{topic_id}.")
    return True


# ==========================================================
# ===== НОВЫЕ ФУНКЦИИ: СИСТЕМА ЛОТЕРЕИ =====================
# ==========================================================

async def get_user_lottery_info(cursor: aiosqlite.Cursor, user_id: int) -> dict:
    """Получает информацию о времени последней игры и получения билета."""
    await cursor.execute(
        "SELECT last_lottery_play, last_free_ticket FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = await cursor.fetchone()
    if result:
        last_play_str, last_ticket_str = result
        last_play_dt = datetime.fromisoformat(last_play_str) if last_play_str else None
        last_ticket_dt = datetime.fromisoformat(last_ticket_str) if last_ticket_str else None
        return {'last_play': last_play_dt, 'last_ticket': last_ticket_dt}
    return {'last_play': None, 'last_ticket': None}

async def grant_daily_ticket(cursor: aiosqlite.Cursor, user_id: int) -> bool:
    """
    Выдает пользователю ежедневный "билет" (право на игру),
    обновляя время последнего получения.
    """
    await cursor.execute(
        "UPDATE users SET last_free_ticket = ? WHERE user_id = ?",
        (datetime.now(), user_id)
    )
    logger.info(f"Granted daily lottery ticket for user {user_id}.")
    return cursor.rowcount > 0

async def play_lottery(cursor: aiosqlite.Cursor, user_id: int, prize_amount: float):
    """
    Помечает, что пользователь сыграл, обновляет время игры
    и начисляет выигрыш на реферальный баланс.
    """
    await cursor.execute(
        """UPDATE users SET 
           last_lottery_play = ?,
           referral_balance = referral_balance + ?
           WHERE user_id = ?""",
        (datetime.now(), prize_amount, user_id)
    )
    logger.info(f"User {user_id} played lottery and won {prize_amount:.2f} RUB.")

async def get_referral_earnings_history(cursor: aiosqlite.Cursor, user_id: int, limit: int = 10) -> List[Tuple]:
    """
    Получает историю последних реферальных начислений для пользователя.
    """
    await cursor.execute(
        """
        SELECT amount, created_at FROM referral_earnings
        WHERE referrer_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit)
    )
    return await cursor.fetchall()