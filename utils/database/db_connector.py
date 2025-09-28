# utils/database/db_connector.py

"""
Модуль для инициализации базы данных и управления схемой.
Включает безопасные миграции для обновления структуры таблиц в продакшене.
"""
import aiosqlite
from utils.logging_config import logger

DB_NAME = 'artbot.db'

async def init_db():
    """
    Инициализирует базу данных, создает все необходимые таблицы и БЕЗОПАСНО
    обновляет их структуру, если это необходимо. Вызывается один раз при старте бота.
    """
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            # --- Создаем таблицы, если они не существуют (это всегда безопасно) ---
            await db.execute('''
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

            await db.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    topic_id INTEGER,
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

            await db.execute('''
                CREATE TABLE IF NOT EXISTS promo_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    total_uses INTEGER NOT NULL,
                    uses_left INTEGER NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS used_promo_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    promo_code TEXT NOT NULL,
                    order_id INTEGER NOT NULL,
                    used_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # --- БЕЗОПАСНАЯ МИГРАЦИЯ СХЕМЫ ---
            
            # 1. Проверяем таблицу 'orders' на наличие столбца 'topic_id'
            async with db.execute("PRAGMA table_info(orders)") as cursor:
                columns = [info[1] for info in await cursor.fetchall()]
                
                if 'topic_id' not in columns:
                    logger.info("MIGRATION: 'topic_id' column not found in 'orders' table. Adding it...")
                    await db.execute("ALTER TABLE orders ADD COLUMN topic_id INTEGER")
                    logger.info("MIGRATION: Successfully added 'topic_id' column.")
                
                # Здесь можно будет добавлять другие проверки в будущем
                # if 'another_column' not in columns:
                #     ...

            await db.commit()
            logger.info("Database initialized and schema is up to date.")

    except Exception as e:
        logger.error(f"Failed to initialize or migrate SQLite database: {e}", exc_info=True)
        raise