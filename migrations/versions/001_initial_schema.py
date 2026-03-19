"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('user_id', sa.BigInteger, primary_key=True),
        sa.Column('username', sa.Text),
        sa.Column('full_name', sa.Text),
        sa.Column('email', sa.Text),
        sa.Column('is_subscribed', sa.SmallInteger, server_default='0'),
        sa.Column('subscription_end', sa.DateTime),
        sa.Column('created_at', sa.DateTime),
        sa.Column('referrer_id', sa.BigInteger),
        sa.Column('referral_balance', sa.Numeric(12, 2), server_default='0.0'),
        sa.Column('last_lottery_play', sa.DateTime),
        sa.Column('last_free_ticket', sa.DateTime),
        sa.Column('invite_link_issued', sa.SmallInteger, server_default='0'),
        sa.Column('subscription_duration', sa.Integer, server_default='0'),
        sa.Column('activated_promo', sa.Text),
    )

    op.create_table(
        'orders',
        sa.Column('order_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger, sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('topic_id', sa.BigInteger),
        sa.Column('username', sa.Text),
        sa.Column('action', sa.Text),
        sa.Column('crypto', sa.Text),
        sa.Column('amount_crypto', sa.Numeric(20, 8)),
        sa.Column('amount_rub', sa.Numeric(12, 2)),
        sa.Column('phone_and_bank', sa.Text),
        sa.Column('created_at', sa.DateTime),
        sa.Column('promo_code_used', sa.Text),
        sa.Column('service_commission_rub', sa.Numeric(12, 2), server_default='0.0'),
        sa.Column('network_fee_rub', sa.Numeric(12, 2), server_default='0.0'),
        sa.Column('status', sa.Text, server_default='processing'),
        # Для предупреждения перед автозакрытием
        sa.Column('warned_at', sa.DateTime),
    )

    op.create_table(
        'promo_codes',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('code', sa.Text, unique=True, nullable=False),
        sa.Column('total_uses', sa.Integer, nullable=False),
        sa.Column('uses_left', sa.Integer, nullable=False),
        sa.Column('discount_amount_rub', sa.Numeric(12, 2), server_default='0.0'),
        # 'percent' — процент от комиссии, 'fixed' — фиксированная сумма в рублях
        sa.Column('discount_type', sa.Text, server_default='percent'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime),
    )

    op.create_table(
        'used_promo_codes',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger, sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('promo_code', sa.Text, nullable=False),
        sa.Column('order_id', sa.Integer, sa.ForeignKey('orders.order_id'), nullable=False),
        sa.Column('used_at', sa.DateTime),
    )

    op.create_table(
        'settings',
        sa.Column('key', sa.Text, primary_key=True),
        sa.Column('value', sa.Text),
    )

    op.create_table(
        'referral_earnings',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('referrer_id', sa.BigInteger, sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('referral_id', sa.BigInteger, sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('order_id', sa.Integer, sa.ForeignKey('orders.order_id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('created_at', sa.DateTime),
    )

    op.create_table(
        'withdrawal_requests',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger, sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', sa.Text, server_default='pending'),
        sa.Column('created_at', sa.DateTime),
        sa.Column('topic_id', sa.BigInteger),
    )

    op.create_table(
        'lottery_plays',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger, sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('prize_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('played_at', sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table('lottery_plays')
    op.drop_table('withdrawal_requests')
    op.drop_table('referral_earnings')
    op.drop_table('settings')
    op.drop_table('used_promo_codes')
    op.drop_table('promo_codes')
    op.drop_table('orders')
    op.drop_table('users')
