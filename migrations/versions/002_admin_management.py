"""Add admins table and is_blocked column

Revision ID: 002
Revises: 001
Create Date: 2026-05-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'admins',
        sa.Column('user_id', sa.BigInteger, primary_key=True),
        sa.Column('username', sa.Text),
        sa.Column('added_at', sa.DateTime),
        sa.Column('added_by', sa.BigInteger),
    )
    op.add_column('users', sa.Column('is_blocked', sa.SmallInteger, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'is_blocked')
    op.drop_table('admins')
