"""Add wallet_ltc to settings

Revision ID: 003
Revises: 002
Create Date: 2026-05-19
"""
from typing import Sequence, Union

from alembic import op

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO settings (key, value) VALUES ('wallet_ltc', '') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key = 'wallet_ltc'")
