"""
Модуль для работы с базой данных.

Этот модуль содержит функции для инициализации базы данных SQLite,
сохранения и получения данных пользователей и заявок.
"""

from datetime import datetime
import aiosqlite
from utils.logging_config import logger

async def init_sqlite():
    """Инициализация базы данных SQLite и создание таблиц."""
    try:
        conn = await aiosqlite.connect('artbot.db')
        async with conn.cursor() as cursor:
            # Создаём таблицу пользователей, если она не существует
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    email TEXT,
                    is_subscribed INTEGER DEFAULT 0,
                    subscription_end DATETIME,
                    created_at DATETIME,
                    invite_link_issued INTEGER DEFAULT 0,
                    subscription_duration INTEGER DEFAULT 0
                )
            ''')
            
            # Создаём таблицу заявок, если она не существует
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_number INTEGER UNIQUE,
                    user_id INTEGER,
                    username TEXT,
                    action TEXT,
                    crypto TEXT,
                    amount_crypto REAL,
                    amount_rub REAL,
                    phone_and_bank TEXT,
                    created_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            # Проверяем, существует ли столбец subscription_duration
            await cursor.execute("PRAGMA table_info(users)")
            columns = [info[1] for info in await cursor.fetchall()]
            if 'subscription_duration' not in columns:
                await cursor.execute('''
                    ALTER TABLE users ADD COLUMN subscription_duration INTEGER DEFAULT 0
                ''')
                logger.info("Added subscription_duration column to users table")
            await conn.commit()
        logger.info("SQLite connected successfully")
        return conn
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error(f"Failed to connect to SQLite: {e}")
        raise

async def create_order(user_id: int, username: str, action: str, crypto: str, 
                      amount_crypto: float, amount_rub: float, phone_and_bank: str) -> int:
    """Создание новой заявки в базе данных.
    
    Args:
        user_id: ID пользователя
        username: Имя пользователя
        action: Действие (sell/buy)
        crypto: Код криптовалюты
        amount_crypto: Сумма в криптовалюте
        amount_rub: Сумма в рублях
        phone_and_bank: Номер телефона и банк
        
    Returns:
        int: Номер созданной заявки
    """
    try:
        conn = await init_sqlite()
        async with conn.cursor() as cursor:
            # Получаем следующий номер заявки (начиная с 10000)
            await cursor.execute("SELECT MAX(order_number) FROM orders")
            result = await cursor.fetchone()
            next_order_number = (result[0] or 9999) + 1
            
            # Создаём заявку
            created_at = datetime.now()
            await cursor.execute('''
                INSERT INTO orders (order_number, user_id, username, action, crypto, 
                                  amount_crypto, amount_rub, phone_and_bank, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (next_order_number, user_id, username, action, crypto, 
                  amount_crypto, amount_rub, phone_and_bank, created_at))
            
            await conn.commit()
            logger.info(f"Created order #{next_order_number} for user {user_id}")
            return next_order_number
            
    except (ConnectionError, TimeoutError, OSError, ValueError) as e:
        logger.error(f"Failed to create order: {e}")
        raise

async def save_or_update_user(user_id: int, username: str, full_name: str, email: str = None) -> bool:
    """Сохранение или обновление данных пользователя.
    
    Args:
        user_id: ID пользователя в Telegram
        username: Имя пользователя в Telegram
        full_name: Полное имя пользователя
        email: Email пользователя (опционально)
        
    Returns:
        bool: True если пользователь новый, False если обновлен
    """
    try:
        conn = await init_sqlite()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            existing_user = await cursor.fetchone()
            is_new_user = existing_user is None
            
            created_at = datetime.now()
            await cursor.execute(
                "INSERT OR REPLACE INTO users (user_id, username, full_name, email, is_subscribed, subscription_end, created_at, invite_link_issued, subscription_duration) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ",
                (user_id, username, full_name, email, 0, None, created_at, 0, 0)
            )
            await conn.commit()
            logger.info(f"User {user_id} {'saved' if is_new_user else 'updated'} in SQLite")
        return is_new_user
    except (ConnectionError, TimeoutError, OSError, ValueError) as e:
        logger.error(f"Failed to save/update user {user_id} in SQLite: {e}")
        return False
    finally:
        await conn.close()

async def get_user_email(user_id: int) -> str:
    try:
        conn = await init_sqlite()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT email FROM users WHERE user_id = ?", (user_id,))
            result = await cursor.fetchone()
            return result[0] if result and result[0] else None
    except (ConnectionError, TimeoutError, OSError, ValueError) as e:
        logger.error(f"Failed to get email for user {user_id}: {e}")
        return None
    finally:
        await conn.close()

async def check_subscription(user_id: int):
    try:
        conn = await init_sqlite()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT is_subscribed, subscription_end, invite_link_issued, subscription_duration FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            if result:
                subscription_end = result[1]
                # Преобразуем subscription_end в datetime, если это строка
                if subscription_end and isinstance(subscription_end, str):
                    try:
                        subscription_end = datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        logger.error(f"Invalid subscription_end format for user {user_id}: {subscription_end}")
                        subscription_end = None
                return {
                    'is_subscribed': bool(result[0]),
                    'subscription_end': subscription_end,
                    'invite_link_issued': bool(result[2]),
                    'subscription_duration': result[3]
                }
            return {'is_subscribed': False, 'subscription_end': None, 'invite_link_issued': False, 'subscription_duration': 0}
    except (ConnectionError, TimeoutError, OSError, ValueError) as e:
        logger.error(f"Failed to check subscription for user {user_id}: {e}")
        return {'is_subscribed': False, 'subscription_end': None, 'invite_link_issued': False, 'subscription_duration': 0}
    finally:
        await conn.close()

async def update_subscription(user_id: int, is_subscribed: bool, subscription_end, invite_link_issued: bool = False, subscription_duration: int = 0):
    try:
        conn = await init_sqlite()
        async with conn.cursor() as cursor:
            # Если subscription_end — строка, преобразуем в datetime
            if subscription_end and isinstance(subscription_end, str):
                try:
                    subscription_end = datetime.strptime(subscription_end, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    logger.error(f"Invalid subscription_end format for user {user_id}: {subscription_end}")
                    subscription_end = None
            # Дополнительная проверка, чтобы избежать сохранения некорректных данных
            if subscription_end and not isinstance(subscription_end, datetime):
                logger.error(f"Invalid subscription_end type for user {user_id}: {type(subscription_end)}")
                subscription_end = None
            await cursor.execute(
                "UPDATE users SET is_subscribed = ?, subscription_end = ?, invite_link_issued = ?, subscription_duration = ? WHERE user_id = ?",
                (is_subscribed, subscription_end, invite_link_issued, subscription_duration, user_id)
            )
            await conn.commit()
            logger.info(f"Subscription updated for user {user_id}: is_subscribed={is_subscribed}, end={subscription_end}, invite_link_issued={invite_link_issued}, duration={subscription_duration}")
    except (ConnectionError, TimeoutError, OSError, ValueError) as e:
        logger.error(f"Failed to update subscription for user {user_id}: {e}")
    finally:
        await conn.close()

async def get_username_by_id(user_id):
    try:
        conn = await init_sqlite()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
            result = await cursor.fetchone()
            return result[0] if result else "Пользователь"
    except (ConnectionError, TimeoutError, OSError, ValueError) as e:
        logger.error(f"Failed to get username for user {user_id}: {e}")
        return "Пользователь"
    finally:
        await conn.close()

async def find_all_users():
    """Получение списка всех пользователей из базы данных.
    
    Returns:
        list: Список кортежей с данными пользователей
    """
    try:
        conn = await init_sqlite()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT user_id, username, full_name, email, is_subscribed, subscription_end, created_at, invite_link_issued, subscription_duration FROM users")
            rows = await cursor.fetchall()
            # Преобразуем subscription_end и created_at в datetime
            result = []
            for row in rows:
                row = list(row)
                # Преобразуем subscription_end
                if row[5] and isinstance(row[5], str):
                    try:
                        row[5] = datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        logger.error(f"Invalid subscription_end format for user {row[0]}: {row[5]}")
                        row[5] = None
                elif row[5] is None:
                    row[5] = None
                # Преобразуем created_at
                if row[6] and isinstance(row[6], str):
                    try:
                        row[6] = datetime.strptime(row[6], '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        logger.error(f"Invalid created_at format for user {row[0]}: {row[6]}")
                        row[6] = None
                elif row[6] is None:
                    row[6] = None
                result.append(tuple(row))
            return result
    except (ConnectionError, TimeoutError, OSError, ValueError) as e:
        logger.error(f"Failed to find all users: {e}")
        return []
    finally:
        await conn.close()