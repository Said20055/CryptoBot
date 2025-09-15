# utils/db_connector.py

"""
Модуль для инициализации базы данных и управления схемой.
"""
import aiosqlite
from utils.logging_config import logger

DB_NAME = 'artbot.db'

async def init_db():
    """
    Инициализирует базу данных, создает все необходимые таблицы и обновляет их структуру.
    Вызывается один раз при старте бота.
    """
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.cursor() as cursor:
                # --- Таблица USERS ---
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
                        subscription_duration INTEGER DEFAULT 0,
                        activated_promo TEXT DEFAULT NULL
                    )
                ''')

                # --- Таблица ORDERS ---
                await cursor.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        username TEXT,
                        action TEXT,
                        crypto TEXT,
                        amount_crypto REAL,
                        amount_rub REAL,
                        phone_and_bank TEXT,
                        created_at DATETIME,
                        promo_code_used TEXT DEFAULT NULL,
                        status TEXT DEFAULT 'processing',
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                await cursor.execute("PRAGMA table_info(orders)")
                columns = [info[1] for info in await cursor.fetchall()]
                if 'status' not in columns:
                    await cursor.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'processing'")
                    logger.info("Added 'status' column to orders table")
                    
                # --- Таблица PROMO_CODES ---
                await cursor.execute('''
                    CREATE TABLE IF NOT EXISTS promo_codes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code TEXT UNIQUE NOT NULL,
                        total_uses INTEGER NOT NULL,
                        uses_left INTEGER NOT NULL,
                        is_active INTEGER DEFAULT 1,
                        created_at DATETIME
                    )
                ''')

                # --- Таблица USED_PROMO_CODES (для истории) ---
                await cursor.execute('''
                    CREATE TABLE IF NOT EXISTS used_promo_codes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        promo_code TEXT NOT NULL,
                        order_id INTEGER NOT NULL,
                        used_at DATETIME,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')

            await db.commit()
            logger.info("Database initialized successfully and tables are up to date.")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite database: {e}", exc_info=True)
        raise