"""add features, fundamentals, signal enrichment

Revision ID: 002
Revises: 001
Create Date: 2026-04-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Expand feature columns
    op.add_column("features", sa.Column("bb_pct_b", sa.Numeric(12, 6), nullable=True))
    op.add_column("features", sa.Column("atr_14",   sa.Numeric(12, 6), nullable=True))
    op.add_column("features", sa.Column("obv",      sa.Numeric(18, 4), nullable=True))
    op.add_column("features", sa.Column("adx_14",   sa.Numeric(12, 6), nullable=True))

    # Enrich signal table
    op.add_column("signals", sa.Column("rationale",       sa.Text(),        nullable=True))
    op.add_column("signals", sa.Column("composite_score", sa.Numeric(5, 4), nullable=True))

    # Fundamental snapshots table (one row per ticker, upserted weekly)
    op.create_table(
        "fundamental_snapshots",
        sa.Column("id",                   sa.Integer(),               nullable=False, autoincrement=True),
        sa.Column("ticker_id",            sa.Integer(),               nullable=False),
        sa.Column("fetched_at",           sa.DateTime(timezone=True), nullable=False),
        sa.Column("pe_ratio",             sa.Numeric(12, 4),          nullable=True),
        sa.Column("forward_pe",           sa.Numeric(12, 4),          nullable=True),
        sa.Column("market_cap",           sa.Numeric(20, 2),          nullable=True),
        sa.Column("analyst_target_price", sa.Numeric(18, 4),          nullable=True),
        sa.Column("week_52_high",         sa.Numeric(18, 4),          nullable=True),
        sa.Column("week_52_low",          sa.Numeric(18, 4),          nullable=True),
        sa.Column("beta",                 sa.Numeric(8, 4),           nullable=True),
        sa.Column("sector",               sa.String(100),             nullable=True),
        sa.Column("industry",             sa.String(200),             nullable=True),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker_id", name="uq_fundamentals_ticker"),
    )
    op.create_index("idx_fundamentals_ticker_id", "fundamental_snapshots", ["ticker_id"])


def downgrade() -> None:
    op.drop_index("idx_fundamentals_ticker_id", table_name="fundamental_snapshots")
    op.drop_table("fundamental_snapshots")
    op.drop_column("signals", "composite_score")
    op.drop_column("signals", "rationale")
    op.drop_column("features", "adx_14")
    op.drop_column("features", "obv")
    op.drop_column("features", "atr_14")
    op.drop_column("features", "bb_pct_b")
