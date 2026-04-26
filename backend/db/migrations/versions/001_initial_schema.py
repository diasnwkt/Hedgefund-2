"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tickers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol"),
    )
    op.create_index("idx_tickers_symbol", "tickers", ["symbol"])

    op.create_table(
        "prices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(18, 4), nullable=False),
        sa.Column("high", sa.Numeric(18, 4), nullable=False),
        sa.Column("low", sa.Numeric(18, 4), nullable=False),
        sa.Column("close", sa.Numeric(18, 4), nullable=False),
        sa.Column("adj_close", sa.Numeric(18, 4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker_id", "date", name="uq_prices_ticker_date"),
    )
    op.create_index("idx_prices_ticker_date", "prices", ["ticker_id", "date"])

    op.create_table(
        "features",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("rsi_14", sa.Numeric(12, 6), nullable=True),
        sa.Column("macd", sa.Numeric(12, 6), nullable=True),
        sa.Column("macd_signal", sa.Numeric(12, 6), nullable=True),
        sa.Column("volume_zscore", sa.Numeric(12, 6), nullable=True),
        sa.Column("ma_20", sa.Numeric(18, 4), nullable=True),
        sa.Column("ma_50", sa.Numeric(18, 4), nullable=True),
        sa.Column("ma_cross", sa.SmallInteger(), nullable=True),
        sa.Column("momentum_5d", sa.Numeric(12, 6), nullable=True),
        sa.Column("momentum_20d", sa.Numeric(12, 6), nullable=True),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker_id", "date", name="uq_features_ticker_date"),
    )

    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signal", sa.String(4), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("executed", sa.Boolean(), nullable=False, server_default="false"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_signals_confidence"),
        sa.CheckConstraint("signal IN ('BUY','SELL','HOLD')", name="ck_signals_signal"),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_signals_generated_at", "signals", ["generated_at"])

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("shares", sa.Numeric(18, 6), nullable=False),
        sa.Column("avg_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("mode", sa.String(5), nullable=False),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("shares", sa.Numeric(18, 6), nullable=False),
        sa.Column("requested_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("filled_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("slippage", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("commission", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("signal_id", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mode", sa.String(5), nullable=False),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"]),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_orders_executed_at", "orders", ["executed_at"])

    op.create_table(
        "equity_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cash", sa.Numeric(18, 4), nullable=False),
        sa.Column("positions_value", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_equity", sa.Numeric(18, 4), nullable=False),
        sa.Column("realized_pnl_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("benchmark_value", sa.Numeric(18, 4), nullable=True),
        sa.Column("mode", sa.String(5), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("timestamp", "mode", name="uq_equity_snapshot_ts_mode"),
    )
    op.create_index("idx_equity_snapshots_mode_ts", "equity_snapshots", ["mode", "timestamp"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("actor", sa.String(50), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_log_timestamp", "audit_log", ["timestamp"])

    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("audit_log")
    op.drop_table("equity_snapshots")
    op.drop_table("orders")
    op.drop_table("positions")
    op.drop_table("signals")
    op.drop_table("features")
    op.drop_table("prices")
    op.drop_table("tickers")
