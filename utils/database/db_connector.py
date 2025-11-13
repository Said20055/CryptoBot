# utils/database/db_connector.py

"""
Модуль для инициализации базы данных и управления схемой.
Включает безопасные миграции для обновления структуры таблиц в продакшене.
"""
import aiosqlite
from config import CRYPTO_WALLETS, SBP_BANK, SBP_PHONE
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
                    referrer_id INTEGER,              
                    referral_balance REAL DEFAULT 0.0,  
                    
                    -- Система лотереи
                    last_lottery_play DATETIME,    
                    last_free_ticket DATETIME ,       
                    
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
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # --- 2. НОВАЯ ТАБЛИЦА: История реферальных начислений ---
            await db.execute('''
                CREATE TABLE IF NOT EXISTS referral_earnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,     -- Кто получил вознаграждение
                    referral_id INTEGER NOT NULL,     -- С чьей сделки
                    order_id INTEGER NOT NULL,        -- ID сделки
                    amount REAL NOT NULL,             -- Сумма вознаграждения в рублях
                    created_at DATETIME,
                    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                    FOREIGN KEY (referral_id) REFERENCES users (user_id),
                    FOREIGN KEY (order_id) REFERENCES orders (order_id)
                )
            ''')

            # --- 3. НОВАЯ ТАБЛИЦА: Заявки на вывод реферальных средств ---
            await db.execute('''
                CREATE TABLE IF NOT EXISTS withdrawal_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'pending',  -- pending, completed, rejected
                    created_at DATETIME,
                    topic_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # --- 4. БЕЗОПАСНАЯ МИГРАЦИЯ СХЕМЫ ---
            
            # Получаем информацию о столбцах в таблице 'users'
            async with db.execute("PRAGMA table_info(users)") as cursor:
                user_columns = [info[1] for info in await cursor.fetchall()]

            # Добавляем новые столбцы, если их нет
            migrations = {
                'referrer_id': 'INTEGER',
                'referral_balance': 'REAL DEFAULT 0.0',
                'last_lottery_play': 'DATETIME',
                'last_free_ticket': 'DATETIME'
            }
            
            for column, definition in migrations.items():
                if column not in user_columns:
                    logger.info(f"MIGRATION: '{column}' column not found in 'users' table. Adding it...")
                    await db.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
                    logger.info(f"MIGRATION: Successfully added '{column}' column.")

            await db.commit()
            logger.info("Database initialized and schema is up to date for new modules.")

    except Exception as e:
        logger.error(f"Failed to initialize or migrate SQLite database: {e}", exc_info=True)
        raise