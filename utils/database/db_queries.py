# utils/database/db_queries.py

"""
Все функции для выполнения запросов к БД.
Принимают asyncpg.Connection (или Transaction) вместо aiosqlite.Cursor.
Параметры передаются как позиционные ($1, $2, ...).
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

import asyncpg
from utils.logging_config import logger


# --- USER QUERIES ---

async def save_or_update_user(conn: asyncpg.Connection, user_id: int, username: str,
                              full_name: str, referrer_id: Optional[int] = None) -> bool:
    """Сохраняет нового пользователя (с реферером) или обновляет существующего.
    Возвращает True если пользователь новый."""
    existing = await conn.fetchval("SELECT 1 FROM users WHERE user_id = $1", user_id)
    is_new_user = existing is None

    if is_new_user:
        await conn.execute(
            "INSERT INTO users (user_id, username, full_name, created_at, referrer_id) VALUES ($1, $2, $3, $4, $5)",
            user_id, username, full_name, datetime.now(), referrer_id
        )
    else:
        await conn.execute(
            "UPDATE users SET username = $1, full_name = $2 WHERE user_id = $3",
            username, full_name, user_id
        )
    logger.info(f"User {user_id} {'saved' if is_new_user else 'updated'}. Referrer ID: {referrer_id if is_new_user else 'N/A'}.")
    return is_new_user


async def find_all_users(conn: asyncpg.Connection) -> List[asyncpg.Record]:
    """Возвращает ID всех пользователей."""
    return await conn.fetch("SELECT user_id FROM users")


async def get_user_profile(conn: asyncpg.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    """Получает профиль пользователя, считая только УСПЕШНЫЕ сделки."""
    user_data = await conn.fetchrow("SELECT username FROM users WHERE user_id = $1", user_id)
    if not user_data:
        return None

    stats_data = await conn.fetchrow(
        "SELECT COUNT(order_id), COALESCE(SUM(amount_rub), 0) FROM orders WHERE user_id = $1 AND status = 'completed'",
        user_id
    )
    return {
        'user_id': user_id,
        'username': user_data['username'],
        'total_orders': stats_data['count'],
        'total_volume_rub': stats_data['coalesce']
    }


# --- ORDER QUERIES ---

async def create_order(conn: asyncpg.Connection, user_id: int, username: str, action: str,
                       crypto: str, amount_crypto: float, amount_rub: float,
                       phone_and_bank: str, promo_code: Optional[str],
                       topic_id: int, service_commission_rub: float = 0.0,
                       network_fee_rub: float = 0.0) -> int:
    """Создает новую заявку и возвращает ее ID."""
    order_id = await conn.fetchval('''
        INSERT INTO orders (user_id, topic_id, username, action, crypto,
                          amount_crypto, amount_rub, phone_and_bank, created_at, promo_code_used,
                          service_commission_rub, network_fee_rub)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING order_id
    ''', user_id, topic_id, username, action, crypto, amount_crypto, amount_rub,
        phone_and_bank, datetime.now(), promo_code, service_commission_rub, network_fee_rub)
    logger.info(f"Created order #{order_id} in topic #{topic_id} for user {user_id}. Promo: {promo_code}")
    return order_id


async def update_order_status(conn: asyncpg.Connection, order_id: int, new_status: str) -> bool:
    """Обновляет статус указанной заявки."""
    allowed_statuses = ['processing', 'completed', 'rejected', 'cancelled_by_user', 'auto_closed']
    if new_status not in allowed_statuses:
        logger.error(f"Attempted to set an invalid order status: {new_status}")
        return False

    if new_status == 'processing':
        status = await conn.execute(
            "UPDATE orders SET status = $1 WHERE order_id = $2",
            new_status, order_id
        )
    else:
        status = await conn.execute(
            "UPDATE orders SET status = $1 WHERE order_id = $2 AND status = 'processing'",
            new_status, order_id
        )
    return status.endswith("1")  # "UPDATE 1" означает успех


async def get_order_status(conn: asyncpg.Connection, order_id: int) -> Optional[str]:
    """Возвращает текущий статус заявки."""
    return await conn.fetchval("SELECT status FROM orders WHERE order_id = $1", order_id)


async def get_active_order_for_user(conn: asyncpg.Connection, user_id: int) -> Optional[dict]:
    """Ищет активную (в обработке) заявку пользователя."""
    logger.info(f"DB Query: Searching for active order for user_id={user_id}")
    row = await conn.fetchrow(
        """
        SELECT order_id, topic_id, action, crypto, amount_crypto, amount_rub, phone_and_bank
        FROM orders
        WHERE user_id = $1 AND status = 'processing'
        """,
        user_id
    )
    if row:
        result = {
            'order_id': row['order_id'], 'topic_id': row['topic_id'], 'action': row['action'],
            'crypto': row['crypto'], 'amount_crypto': row['amount_crypto'],
            'total_amount': row['amount_rub'], 'user_input': row['phone_and_bank']
        }
        logger.info(f"DB Query: Found active order for user_id={user_id}.")
        return result

    logger.info(f"DB Query: No active order found for user_id={user_id}.")
    return None


async def get_order_by_topic_id(conn: asyncpg.Connection, topic_id: int) -> Optional[dict]:
    """Ищет заявку по ID темы в Telegram."""
    row = await conn.fetchrow(
        "SELECT order_id, user_id FROM orders WHERE topic_id = $1",
        topic_id
    )
    if row:
        return {'order_id': row['order_id'], 'user_id': row['user_id']}
    return None


async def get_order_by_id(conn: asyncpg.Connection, order_id: int) -> Optional[dict]:
    """Возвращает полную информацию о заявке по ее ID."""
    row = await conn.fetchrow(
        "SELECT topic_id, status, amount_rub, service_commission_rub, network_fee_rub FROM orders WHERE order_id = $1",
        order_id
    )
    if row:
        return {
            'topic_id': row['topic_id'],
            'status': row['status'],
            'amount_rub': row['amount_rub'],
            'service_commission_rub': row['service_commission_rub'] or 0.0,
            'network_fee_rub': row['network_fee_rub'] or 0.0
        }
    return None


async def get_stale_processing_orders(conn: asyncpg.Connection, older_than_minutes: int) -> List[dict]:
    """Возвращает заявки в статусе processing старше заданного количества минут."""
    cutoff = datetime.now() - timedelta(minutes=older_than_minutes)
    rows = await conn.fetch(
        """
        SELECT order_id, user_id, topic_id, created_at
        FROM orders
        WHERE status = 'processing' AND created_at <= $1
        """,
        cutoff
    )
    return [
        {'order_id': r['order_id'], 'user_id': r['user_id'],
         'topic_id': r['topic_id'], 'created_at': r['created_at']}
        for r in rows
    ]


async def get_orders_needing_warning(conn: asyncpg.Connection,
                                     auto_close_minutes: int,
                                     warn_before_minutes: int = 5) -> List[dict]:
    """Возвращает заявки, которым осталось warn_before_minutes до автозакрытия и ещё не было предупреждения."""
    warn_cutoff = datetime.now() - timedelta(minutes=auto_close_minutes - warn_before_minutes)
    close_cutoff = datetime.now() - timedelta(minutes=auto_close_minutes)
    rows = await conn.fetch(
        """
        SELECT order_id, user_id, topic_id, created_at
        FROM orders
        WHERE status = 'processing'
          AND created_at <= $1
          AND created_at > $2
          AND warned_at IS NULL
        """,
        warn_cutoff, close_cutoff
    )
    return [
        {'order_id': r['order_id'], 'user_id': r['user_id'],
         'topic_id': r['topic_id'], 'created_at': r['created_at']}
        for r in rows
    ]


async def mark_order_warned(conn: asyncpg.Connection, order_id: int) -> None:
    """Помечает заявку как предупреждённую (warned_at = NOW())."""
    await conn.execute(
        "UPDATE orders SET warned_at = $1 WHERE order_id = $2",
        datetime.now(), order_id
    )


async def get_processing_orders(conn: asyncpg.Connection) -> List[dict]:
    """Возвращает все заявки в статусе processing для напоминаний админам."""
    rows = await conn.fetch(
        "SELECT order_id, user_id, created_at FROM orders WHERE status = 'processing' ORDER BY created_at ASC"
    )
    return [{'order_id': r['order_id'], 'user_id': r['user_id'], 'created_at': r['created_at']} for r in rows]


async def get_user_orders_page(conn: asyncpg.Connection, user_id: int,
                               limit: int = 5, offset: int = 0) -> List[dict]:
    """Возвращает страницу истории заказов пользователя (для пагинации)."""
    rows = await conn.fetch(
        """
        SELECT order_id, action, crypto, amount_rub, status, created_at
        FROM orders WHERE user_id = $1
        ORDER BY created_at DESC LIMIT $2 OFFSET $3
        """,
        user_id, limit, offset
    )
    return [
        {
            'order_id': r['order_id'], 'action': r['action'], 'crypto': r['crypto'],
            'amount_rub': r['amount_rub'], 'status': r['status'], 'created_at': r['created_at']
        }
        for r in rows
    ]


async def count_user_orders(conn: asyncpg.Connection, user_id: int) -> int:
    """Возвращает общее количество заявок пользователя (для пагинации)."""
    return await conn.fetchval("SELECT COUNT(*) FROM orders WHERE user_id = $1", user_id)


# --- PROMO CODE QUERIES ---

async def add_promo_code(conn: asyncpg.Connection, code: str, total_uses: int,
                         discount_amount: float, discount_type: str = 'percent') -> bool:
    """Добавляет новый промокод. discount_type: 'percent' или 'fixed' (руб)."""
    try:
        await conn.execute(
            """INSERT INTO promo_codes (code, total_uses, uses_left, discount_amount_rub, discount_type, created_at)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            code.upper(), total_uses, total_uses, discount_amount, discount_type, datetime.now()
        )
        return True
    except asyncpg.UniqueViolationError:
        return False


async def activate_promo_for_user(conn: asyncpg.Connection, user_id: int, code: str) -> str:
    """Активирует промокод для пользователя. Возвращает статус строкой."""
    code = code.upper()

    already = await conn.fetchval(
        "SELECT 1 FROM used_promo_codes WHERE user_id = $1 AND promo_code = $2", user_id, code
    )
    if already:
        return "already_redeemed"

    active = await conn.fetchval("SELECT activated_promo FROM users WHERE user_id = $1", user_id)
    if active:
        return "already_active"

    promo = await conn.fetchrow(
        "SELECT uses_left, is_active, discount_amount_rub FROM promo_codes WHERE code = $1", code
    )
    if not promo or not promo['is_active'] or promo['uses_left'] < 1:
        return "invalid_or_expired"

    await conn.execute("UPDATE users SET activated_promo = $1 WHERE user_id = $2", code, user_id)
    return "success"


async def get_user_activated_promo(conn: asyncpg.Connection, user_id: int) -> Optional[str]:
    """Возвращает активный промокод пользователя."""
    return await conn.fetchval("SELECT activated_promo FROM users WHERE user_id = $1", user_id)


async def clear_user_activated_promo(conn: asyncpg.Connection, user_id: int) -> None:
    """Очищает активный промокод пользователя."""
    await conn.execute("UPDATE users SET activated_promo = NULL WHERE user_id = $1", user_id)


async def get_promo_discount_info(conn: asyncpg.Connection, promo_code: str) -> Tuple[float, str]:
    """Возвращает (сумма_скидки, тип_скидки). Тип: 'percent' или 'fixed'."""
    row = await conn.fetchrow(
        "SELECT discount_amount_rub, discount_type FROM promo_codes WHERE code = $1 AND is_active = TRUE",
        promo_code.upper()
    )
    if row:
        return float(row['discount_amount_rub']), row['discount_type']
    return 0.0, 'percent'



async def use_activated_promo(conn: asyncpg.Connection, user_id: int, order_id: int) -> bool:
    """'Сжигает' промокод, привязанный к заявке."""
    promo_code = await conn.fetchval(
        "SELECT promo_code_used FROM orders WHERE order_id = $1", order_id
    )
    if not promo_code:
        return False

    await conn.execute(
        "UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code = $1", promo_code
    )
    await conn.execute(
        "INSERT INTO used_promo_codes (user_id, promo_code, order_id, used_at) VALUES ($1, $2, $3, $4)",
        user_id, promo_code, order_id, datetime.now()
    )
    return True


async def refund_promo_if_needed(conn: asyncpg.Connection, user_id: int, order_id: int) -> None:
    """'Возвращает' промокод пользователю, если заявка отменена."""
    promo_to_refund = await conn.fetchval(
        "SELECT promo_code_used FROM orders WHERE order_id = $1", order_id
    )
    if not promo_to_refund:
        return

    await conn.execute(
        "DELETE FROM used_promo_codes WHERE user_id = $1 AND promo_code = $2 AND order_id = $3",
        user_id, promo_to_refund, order_id
    )

    existing_promo = await conn.fetchval("SELECT activated_promo FROM users WHERE user_id = $1", user_id)
    if existing_promo:
        logger.warning(f"Not refunding '{promo_to_refund}' because user {user_id} has another active promo.")
        return

    await conn.execute("UPDATE users SET activated_promo = $1 WHERE user_id = $2", promo_to_refund, user_id)
    logger.info(f"Refunded promo '{promo_to_refund}' to user {user_id} for rejected order #{order_id}.")


# --- SETTINGS ---

async def get_all_settings(conn: asyncpg.Connection) -> dict:
    """Возвращает все настройки из БД в виде словаря."""
    rows = await conn.fetch("SELECT key, value FROM settings")
    return {r['key']: r['value'] for r in rows}


async def update_setting(conn: asyncpg.Connection, key: str, value: str) -> None:
    """Обновляет или вставляет настройку (UPSERT)."""
    await conn.execute(
        "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value",
        key, value
    )


# --- REFERRAL ---

async def get_user_referral_info(conn: asyncpg.Connection, user_id: int) -> dict:
    """Получает реферальную информацию о пользователе."""
    user_data = await conn.fetchrow(
        "SELECT referral_balance, referrer_id FROM users WHERE user_id = $1", user_id
    )
    balance = float(user_data['referral_balance']) if user_data else 0.0
    referrer_id = user_data['referrer_id'] if user_data else None

    referral_count = await conn.fetchval(
        "SELECT COUNT(user_id) FROM users WHERE referrer_id = $1", user_id
    )
    return {'balance': balance, 'referrer_id': referrer_id, 'referral_count': referral_count}


async def add_referral_earning(conn: asyncpg.Connection, order_id: int, referral_id: int,
                               order_amount: float, percentage: float) -> bool:
    """Находит реферера, начисляет ему процент и записывает в историю."""
    referrer_id = await conn.fetchval(
        "SELECT referrer_id FROM users WHERE user_id = $1", referral_id
    )
    if not referrer_id:
        return False

    earning_amount = order_amount * (percentage / 100.0)

    await conn.execute(
        "UPDATE users SET referral_balance = referral_balance + $1 WHERE user_id = $2",
        earning_amount, referrer_id
    )
    await conn.execute(
        "INSERT INTO referral_earnings (referrer_id, referral_id, order_id, amount, created_at) VALUES ($1, $2, $3, $4, $5)",
        referrer_id, referral_id, order_id, earning_amount, datetime.now()
    )
    logger.info(f"User {referrer_id} earned {earning_amount:.2f} RUB from referral {referral_id}'s order #{order_id}.")
    return True


async def create_withdrawal_request(conn: asyncpg.Connection, user_id: int, amount: float, topic_id: int) -> bool:
    """Создает заявку на вывод и обнуляет баланс пользователя."""
    status = await conn.execute(
        "UPDATE users SET referral_balance = 0.0 WHERE user_id = $1", user_id
    )
    if status == "UPDATE 0":
        return False

    await conn.execute(
        "INSERT INTO withdrawal_requests (user_id, amount, created_at, topic_id) VALUES ($1, $2, $3, $4)",
        user_id, amount, datetime.now(), topic_id
    )
    logger.info(f"User {user_id} created a withdrawal request for {amount:.2f} RUB in topic #{topic_id}.")
    return True


async def get_referral_earnings_history(conn: asyncpg.Connection, user_id: int, limit: int = 10) -> List[asyncpg.Record]:
    """Получает историю последних реферальных начислений."""
    return await conn.fetch(
        "SELECT amount, created_at FROM referral_earnings WHERE referrer_id = $1 ORDER BY created_at DESC LIMIT $2",
        user_id, limit
    )


# --- LOTTERY ---

async def get_user_lottery_info(conn: asyncpg.Connection, user_id: int) -> dict:
    """Получает информацию о времени последней игры и получения билета."""
    row = await conn.fetchrow(
        "SELECT last_lottery_play, last_free_ticket FROM users WHERE user_id = $1", user_id
    )
    if row:
        return {'last_play': row['last_lottery_play'], 'last_ticket': row['last_free_ticket']}
    return {'last_play': None, 'last_ticket': None}


async def grant_daily_ticket(conn: asyncpg.Connection, user_id: int) -> bool:
    """Выдает пользователю ежедневный билет."""
    status = await conn.execute(
        "UPDATE users SET last_free_ticket = $1 WHERE user_id = $2", datetime.now(), user_id
    )
    logger.info(f"Granted daily lottery ticket for user {user_id}.")
    return status.endswith("1")


async def play_lottery(conn: asyncpg.Connection, user_id: int, prize_amount: float) -> bool:
    """Помечает факт игры, начисляет выигрыш и записывает в историю."""
    status = await conn.execute(
        """UPDATE users SET
           last_lottery_play = $1,
           referral_balance = referral_balance + $2
           WHERE user_id = $3""",
        datetime.now(), prize_amount, user_id
    )
    if status == "UPDATE 0":
        return False

    await conn.execute(
        "INSERT INTO lottery_plays (user_id, prize_amount, played_at) VALUES ($1, $2, $3)",
        user_id, prize_amount, datetime.now()
    )
    logger.info(f"User {user_id} played lottery and won {prize_amount:.2f} RUB.")
    return True


# --- ADMIN STATISTICS ---

async def get_admin_statistics(conn: asyncpg.Connection) -> dict:
    """Собирает статистику по пользователям и лотерее."""
    now = datetime.now()

    users_day = await conn.fetchval(
        "SELECT COUNT(user_id) FROM users WHERE created_at >= $1", now - timedelta(days=1)
    )
    users_week = await conn.fetchval(
        "SELECT COUNT(user_id) FROM users WHERE created_at >= $1", now - timedelta(days=7)
    )
    users_month = await conn.fetchval(
        "SELECT COUNT(user_id) FROM users WHERE created_at >= $1", now - timedelta(days=30)
    )
    lottery_day = await conn.fetchval(
        "SELECT COUNT(id) FROM lottery_plays WHERE played_at >= $1", now - timedelta(days=1)
    )

    return {
        'users_day': users_day,
        'users_week': users_week,
        'users_month': users_month,
        'lottery_day': lottery_day,
    }
