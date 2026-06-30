"""Add operator_responded_at to orders

Revision ID: 004
Revises: 003
Create Date: 2026-06-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('operator_responded_at', sa.DateTime, nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'operator_responded_at')
