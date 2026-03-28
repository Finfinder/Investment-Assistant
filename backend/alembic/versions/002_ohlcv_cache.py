"""create ohlcv_cache table

Revision ID: 002_ohlcv_cache
Revises: 001_initial
Create Date: 2026-03-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_ohlcv_cache"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ohlcv_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_ohlcv_cache_symbol_tf_ts"),
    )
    op.create_index("ix_ohlcv_cache_symbol_timeframe", "ohlcv_cache", ["symbol", "timeframe"])


def downgrade() -> None:
    op.drop_index("ix_ohlcv_cache_symbol_timeframe", table_name="ohlcv_cache")
    op.drop_table("ohlcv_cache")
