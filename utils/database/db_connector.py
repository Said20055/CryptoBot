# utils/database/db_connector.py

"""
Инициализация БД: запускает Alembic-миграции при старте бота.
Логика схемы вынесена в migrations/versions/.
"""

from alembic.config import Config
from alembic import command
from utils.logging_config import logger


def run_migrations() -> None:
    """Синхронно выполняет все pending Alembic-миграции (вызывается из on_startup)."""
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully.")
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}", exc_info=True)
        raise
