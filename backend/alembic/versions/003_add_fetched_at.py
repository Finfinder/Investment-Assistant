"""add fetched_at column to ohlcv_cache

Revision ID: 003_add_fetched_at
Revises: 002_ohlcv_cache
Create Date: 2026-03-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_add_fetched_at"
down_revision: str | None = "002_ohlcv_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ohlcv_cache", sa.Column("fetched_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    op.drop_column("ohlcv_cache", "fetched_at")
