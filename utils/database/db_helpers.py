"""
Контекстные менеджеры для работы с пулом asyncpg.

transaction() — для операций записи (автоматический rollback при ошибке).
acquire()      — для SELECT-запросов без транзакции.
"""

from contextlib import asynccontextmanager

from .connection import get_pool


@asynccontextmanager
async def transaction():
    """Соединение из пула + транзакция с автоматическим rollback при исключении."""
    async with get_pool().acquire() as conn:
        async with conn.transaction():
            yield conn


@asynccontextmanager
async def acquire():
    """Соединение из пула без транзакции (для SELECT-запросов)."""
    async with get_pool().acquire() as conn:
        yield conn
