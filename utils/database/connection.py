"""
Управление пулом соединений с PostgreSQL через asyncpg.

Пул инициализируется один раз при старте бота (on_startup) и закрывается при завершении.
Все остальные модули получают соединение через контекстный менеджер transaction() из db_helpers.
"""

import asyncpg
from loguru import logger

_pool: asyncpg.Pool | None = None


async def init_pool(dsn: str) -> None:
    global _pool
    _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    logger.info("PostgreSQL connection pool initialized")


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL connection pool closed")


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call init_pool() first.")
    return _pool
