"""
Скрипт миграции данных из SQLite (artbot.db) в PostgreSQL.

Запуск:
    python migrate_sqlite_to_pg.py --sqlite /path/to/artbot.db

Что делает:
    1. Читает схему SQLite и сопоставляет с таблицами PostgreSQL
    2. Переносит данные в правильном порядке (с учётом FK-зависимостей)
    3. Пропускает дубликаты (ON CONFLICT DO NOTHING)
    4. Подробно логирует каждый шаг и все ошибки
    5. Не трогает уже существующие данные в PostgreSQL

Требования:
    pip install asyncpg aiosqlite python-dotenv
"""

import argparse
import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Optional

import asyncpg
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("migration.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_dt(value: Any) -> Optional[datetime]:
    """Конвертирует строку/None в datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    log.warning("Не удалось распарсить дату: %r — установлено NULL", value)
    return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def sqlite_tables(cur: sqlite3.Cursor) -> set:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cur.fetchall()}


def sqlite_columns(cur: sqlite3.Cursor, table: str) -> set:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def col(row: sqlite3.Row, name: str, default: Any = None) -> Any:
    """Безопасное чтение поля: возвращает default, если колонки нет."""
    try:
        return row[name]
    except IndexError:
        return default


# ---------------------------------------------------------------------------
# Migration steps
# ---------------------------------------------------------------------------

async def migrate_users(sqlite_cur: sqlite3.Cursor, pg: asyncpg.Connection) -> int:
    log.info("=== Миграция: users ===")
    cols = sqlite_columns(sqlite_cur, "users")

    sqlite_cur.execute("SELECT * FROM users")
    rows = sqlite_cur.fetchall()
    log.info("  Найдено записей в SQLite: %d", len(rows))

    inserted = skipped = errors = 0
    for row in rows:
        try:
            user_id   = safe_int(col(row, "user_id"))
            username  = col(row, "username")
            full_name = col(row, "full_name") or col(row, "name") or ""
            created_at = parse_dt(col(row, "created_at")) or datetime.now()
            referrer_id = safe_int(col(row, "referrer_id")) or None
            referral_balance = safe_float(col(row, "referral_balance", 0.0))
            activated_promo = col(row, "activated_promo")
            last_lottery = parse_dt(col(row, "last_lottery_play"))
            last_ticket  = parse_dt(col(row, "last_free_ticket"))

            result = await pg.execute(
                """
                INSERT INTO users (
                    user_id, username, full_name, created_at,
                    referrer_id, referral_balance, activated_promo,
                    last_lottery_play, last_free_ticket
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                ON CONFLICT (user_id) DO NOTHING
                """,
                user_id, username, full_name, created_at,
                referrer_id, referral_balance, activated_promo,
                last_lottery, last_ticket,
            )
            if result == "INSERT 0 1":
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            log.error("  [users] Ошибка для user_id=%s: %s", col(row, "user_id"), e)
            errors += 1

    log.info("  Результат: вставлено=%d  пропущено=%d  ошибок=%d", inserted, skipped, errors)
    return inserted


async def migrate_orders(sqlite_cur: sqlite3.Cursor, pg: asyncpg.Connection) -> dict:
    """Возвращает маппинг old_order_id -> new_order_id (если autoincrement сбросился)."""
    log.info("=== Миграция: orders ===")

    sqlite_cur.execute("SELECT * FROM orders ORDER BY order_id ASC")
    rows = sqlite_cur.fetchall()
    log.info("  Найдено записей в SQLite: %d", len(rows))

    inserted = skipped = errors = 0
    id_map: dict[int, int] = {}

    for row in rows:
        try:
            old_id = safe_int(col(row, "order_id") or col(row, "id"))
            user_id = safe_int(col(row, "user_id"))

            # Проверяем существование пользователя в PG
            exists = await pg.fetchval("SELECT 1 FROM users WHERE user_id=$1", user_id)
            if not exists:
                log.warning("  [orders] order_id=%d: user_id=%d не найден в PG, пропускаем", old_id, user_id)
                skipped += 1
                continue

            status = col(row, "status") or "processing"
            allowed_statuses = {"processing", "completed", "rejected", "cancelled_by_user", "auto_closed"}
            if status not in allowed_statuses:
                log.warning("  [orders] order_id=%d: неизвестный статус '%s', заменяем на 'completed'", old_id, status)
                status = "completed"

            action = col(row, "action") or "buy"
            if action not in ("buy", "sell"):
                action = "buy"

            new_id = await pg.fetchval(
                """
                INSERT INTO orders (
                    user_id, topic_id, username, action, crypto,
                    amount_crypto, amount_rub, phone_and_bank, created_at,
                    promo_code_used, service_commission_rub, network_fee_rub, status
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                ON CONFLICT DO NOTHING
                RETURNING order_id
                """,
                user_id,
                safe_int(col(row, "topic_id")) or None,
                col(row, "username"),
                action,
                col(row, "crypto") or "BTC",
                safe_float(col(row, "amount_crypto")),
                safe_float(col(row, "amount_rub")),
                col(row, "phone_and_bank") or col(row, "requisites") or "",
                parse_dt(col(row, "created_at")) or datetime.now(),
                col(row, "promo_code_used"),
                safe_float(col(row, "service_commission_rub")),
                safe_float(col(row, "network_fee_rub")),
                status,
            )

            if new_id:
                id_map[old_id] = new_id
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            log.error("  [orders] Ошибка для order_id=%s: %s", col(row, "order_id"), e)
            errors += 1

    log.info("  Результат: вставлено=%d  пропущено=%d  ошибок=%d", inserted, skipped, errors)
    return id_map


async def migrate_promo_codes(sqlite_cur: sqlite3.Cursor, pg: asyncpg.Connection) -> int:
    log.info("=== Миграция: promo_codes ===")

    sqlite_cur.execute("SELECT * FROM promo_codes")
    rows = sqlite_cur.fetchall()
    log.info("  Найдено записей в SQLite: %d", len(rows))

    inserted = skipped = errors = 0
    for row in rows:
        try:
            code = (col(row, "code") or "").upper().strip()
            if not code:
                log.warning("  [promo_codes] Пустой код, пропускаем")
                skipped += 1
                continue

            total_uses = safe_int(col(row, "total_uses"), 1)
            uses_left  = safe_int(col(row, "uses_left"), total_uses)
            discount   = safe_float(col(row, "discount_amount_rub") or col(row, "discount_amount"))
            dtype      = col(row, "discount_type") or "percent"
            if dtype not in ("percent", "fixed"):
                dtype = "percent"
            is_active  = bool(col(row, "is_active") if col(row, "is_active") is not None else True)
            created_at = parse_dt(col(row, "created_at")) or datetime.now()

            result = await pg.execute(
                """
                INSERT INTO promo_codes (
                    code, total_uses, uses_left, discount_amount_rub,
                    discount_type, is_active, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (code) DO NOTHING
                """,
                code, total_uses, uses_left, discount, dtype, is_active, created_at,
            )
            if result == "INSERT 0 1":
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            log.error("  [promo_codes] Ошибка для code=%s: %s", col(row, "code"), e)
            errors += 1

    log.info("  Результат: вставлено=%d  пропущено=%d  ошибок=%d", inserted, skipped, errors)
    return inserted


async def migrate_used_promos(sqlite_cur: sqlite3.Cursor, pg: asyncpg.Connection, order_id_map: dict) -> int:
    log.info("=== Миграция: used_promo_codes ===")

    sqlite_cur.execute("SELECT * FROM used_promo_codes")
    rows = sqlite_cur.fetchall()
    log.info("  Найдено записей в SQLite: %d", len(rows))

    inserted = skipped = errors = 0
    for row in rows:
        try:
            user_id  = safe_int(col(row, "user_id"))
            promo    = col(row, "promo_code") or col(row, "code")
            old_oid  = safe_int(col(row, "order_id"))
            new_oid  = order_id_map.get(old_oid)

            if not new_oid:
                log.warning("  [used_promo] order_id=%d не найден в маппинге, пропускаем", old_oid)
                skipped += 1
                continue

            exists_user = await pg.fetchval("SELECT 1 FROM users WHERE user_id=$1", user_id)
            if not exists_user:
                skipped += 1
                continue

            result = await pg.execute(
                """
                INSERT INTO used_promo_codes (user_id, promo_code, order_id, used_at)
                VALUES ($1,$2,$3,$4)
                ON CONFLICT DO NOTHING
                """,
                user_id, promo, new_oid, parse_dt(col(row, "used_at")) or datetime.now(),
            )
            if result == "INSERT 0 1":
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            log.error("  [used_promo] Ошибка: %s", e)
            errors += 1

    log.info("  Результат: вставлено=%d  пропущено=%d  ошибок=%d", inserted, skipped, errors)
    return inserted


async def migrate_referral_earnings(sqlite_cur: sqlite3.Cursor, pg: asyncpg.Connection, order_id_map: dict) -> int:
    log.info("=== Миграция: referral_earnings ===")

    sqlite_cur.execute("SELECT * FROM referral_earnings")
    rows = sqlite_cur.fetchall()
    log.info("  Найдено записей в SQLite: %d", len(rows))

    inserted = skipped = errors = 0
    for row in rows:
        try:
            referrer_id = safe_int(col(row, "referrer_id"))
            referral_id = safe_int(col(row, "referral_id"))
            old_oid     = safe_int(col(row, "order_id"))
            new_oid     = order_id_map.get(old_oid)
            amount      = safe_float(col(row, "amount"))

            if not new_oid:
                log.warning("  [ref_earnings] order_id=%d не найден, пропускаем", old_oid)
                skipped += 1
                continue

            for uid in (referrer_id, referral_id):
                if not await pg.fetchval("SELECT 1 FROM users WHERE user_id=$1", uid):
                    raise ValueError(f"user_id={uid} не найден в PG")

            result = await pg.execute(
                """
                INSERT INTO referral_earnings (referrer_id, referral_id, order_id, amount, created_at)
                VALUES ($1,$2,$3,$4,$5)
                ON CONFLICT DO NOTHING
                """,
                referrer_id, referral_id, new_oid, amount,
                parse_dt(col(row, "created_at")) or datetime.now(),
            )
            if result == "INSERT 0 1":
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            log.error("  [ref_earnings] Ошибка: %s", e)
            errors += 1

    log.info("  Результат: вставлено=%d  пропущено=%d  ошибок=%d", inserted, skipped, errors)
    return inserted


async def migrate_withdrawal_requests(sqlite_cur: sqlite3.Cursor, pg: asyncpg.Connection) -> int:
    log.info("=== Миграция: withdrawal_requests ===")

    sqlite_cur.execute("SELECT * FROM withdrawal_requests")
    rows = sqlite_cur.fetchall()
    log.info("  Найдено записей в SQLite: %d", len(rows))

    inserted = skipped = errors = 0
    for row in rows:
        try:
            user_id = safe_int(col(row, "user_id"))
            amount  = safe_float(col(row, "amount"))
            status  = col(row, "status") or "pending"
            topic_id = safe_int(col(row, "topic_id")) or None
            created_at = parse_dt(col(row, "created_at")) or datetime.now()

            if not await pg.fetchval("SELECT 1 FROM users WHERE user_id=$1", user_id):
                skipped += 1
                continue

            result = await pg.execute(
                """
                INSERT INTO withdrawal_requests (user_id, amount, status, created_at, topic_id)
                VALUES ($1,$2,$3,$4,$5)
                ON CONFLICT DO NOTHING
                """,
                user_id, amount, status, created_at, topic_id,
            )
            if result == "INSERT 0 1":
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            log.error("  [withdrawals] Ошибка: %s", e)
            errors += 1

    log.info("  Результат: вставлено=%d  пропущено=%d  ошибок=%d", inserted, skipped, errors)
    return inserted


async def migrate_lottery_plays(sqlite_cur: sqlite3.Cursor, pg: asyncpg.Connection) -> int:
    log.info("=== Миграция: lottery_plays ===")

    sqlite_cur.execute("SELECT * FROM lottery_plays")
    rows = sqlite_cur.fetchall()
    log.info("  Найдено записей в SQLite: %d", len(rows))

    inserted = skipped = errors = 0
    for row in rows:
        try:
            user_id = safe_int(col(row, "user_id"))
            prize   = safe_float(col(row, "prize_amount"))
            played  = parse_dt(col(row, "played_at")) or datetime.now()

            if not await pg.fetchval("SELECT 1 FROM users WHERE user_id=$1", user_id):
                skipped += 1
                continue

            result = await pg.execute(
                """
                INSERT INTO lottery_plays (user_id, prize_amount, played_at)
                VALUES ($1,$2,$3)
                ON CONFLICT DO NOTHING
                """,
                user_id, prize, played,
            )
            if result == "INSERT 0 1":
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            log.error("  [lottery] Ошибка: %s", e)
            errors += 1

    log.info("  Результат: вставлено=%d  пропущено=%d  ошибок=%d", inserted, skipped, errors)
    return inserted


async def migrate_settings(sqlite_cur: sqlite3.Cursor, pg: asyncpg.Connection) -> int:
    log.info("=== Миграция: settings ===")

    sqlite_cur.execute("SELECT * FROM settings")
    rows = sqlite_cur.fetchall()
    log.info("  Найдено записей в SQLite: %d", len(rows))

    inserted = errors = 0
    for row in rows:
        try:
            key   = col(row, "key") or col(row, "name")
            value = col(row, "value")
            await pg.execute(
                "INSERT INTO settings (key, value) VALUES ($1,$2) ON CONFLICT (key) DO NOTHING",
                str(key), str(value) if value is not None else None,
            )
            inserted += 1
        except Exception as e:
            log.error("  [settings] Ошибка: %s", e)
            errors += 1

    log.info("  Результат: обработано=%d  ошибок=%d", inserted, errors)
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(sqlite_path: str, pg_url: str, dry_run: bool = False):
    log.info("Старт миграции SQLite → PostgreSQL")
    log.info("  SQLite: %s", sqlite_path)
    log.info("  PostgreSQL: %s", pg_url.split("@")[-1])  # скрываем credentials
    log.info("  Режим: %s", "DRY RUN (изменений нет)" if dry_run else "ЗАПИСЬ")

    if not os.path.exists(sqlite_path):
        log.error("Файл SQLite не найден: %s", sqlite_path)
        return

    # Открываем SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    existing_tables = sqlite_tables(sqlite_cur)
    log.info("Таблицы в SQLite: %s", existing_tables)

    # Подключаемся к PostgreSQL
    try:
        pg = await asyncpg.connect(pg_url)
    except Exception as e:
        log.error("Не удалось подключиться к PostgreSQL: %s", e)
        sqlite_conn.close()
        return

    try:
        if dry_run:
            log.info("DRY RUN: подключение успешно, данные не записываются.")
            return

        # Порядок важен из-за FK-зависимостей
        if "users" in existing_tables:
            await migrate_users(sqlite_cur, pg)
        else:
            log.warning("Таблица users отсутствует в SQLite — пропускаем")

        if "promo_codes" in existing_tables:
            await migrate_promo_codes(sqlite_cur, pg)
        else:
            log.warning("Таблица promo_codes отсутствует в SQLite — пропускаем")

        order_id_map: dict = {}
        if "orders" in existing_tables:
            order_id_map = await migrate_orders(sqlite_cur, pg)
        else:
            log.warning("Таблица orders отсутствует в SQLite — пропускаем")

        if "used_promo_codes" in existing_tables:
            await migrate_used_promos(sqlite_cur, pg, order_id_map)
        else:
            log.warning("Таблица used_promo_codes отсутствует в SQLite — пропускаем")

        if "referral_earnings" in existing_tables:
            await migrate_referral_earnings(sqlite_cur, pg, order_id_map)
        else:
            log.warning("Таблица referral_earnings отсутствует в SQLite — пропускаем")

        if "withdrawal_requests" in existing_tables:
            await migrate_withdrawal_requests(sqlite_cur, pg)
        else:
            log.warning("Таблица withdrawal_requests отсутствует в SQLite — пропускаем")

        if "lottery_plays" in existing_tables:
            await migrate_lottery_plays(sqlite_cur, pg)
        else:
            log.warning("Таблица lottery_plays отсутствует в SQLite — пропускаем")

        if "settings" in existing_tables:
            await migrate_settings(sqlite_cur, pg)
        else:
            log.warning("Таблица settings отсутствует в SQLite — пропускаем")

        log.info("=== Миграция завершена. Лог сохранён в migration.log ===")

    finally:
        await pg.close()
        sqlite_conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite → PostgreSQL")
    parser.add_argument("--sqlite", default="artbot.db", help="Путь к SQLite файлу (default: artbot.db)")
    parser.add_argument("--pg-url", default=None, help="PostgreSQL URL (по умолчанию берётся из DATABASE_URL в .env)")
    parser.add_argument("--dry-run", action="store_true", help="Проверить подключение без записи данных")
    args = parser.parse_args()

    pg_url = args.pg_url or os.getenv("DATABASE_URL")
    if not pg_url:
        log.error("DATABASE_URL не задан. Укажите --pg-url или добавьте в .env")
        return

    # asyncpg требует postgresql://, не postgresql+asyncpg://
    pg_url = pg_url.replace("postgresql+asyncpg://", "postgresql://")

    asyncio.run(run(args.sqlite, pg_url, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
