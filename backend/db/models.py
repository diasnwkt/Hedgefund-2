from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Ticker(Base):
    __tablename__ = "tickers"
    __table_args__ = (Index("idx_tickers_symbol", "symbol"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    prices: Mapped[list["Price"]] = relationship(back_populates="ticker", cascade="all, delete-orphan")
    features: Mapped[list["Feature"]] = relationship(back_populates="ticker", cascade="all, delete-orphan")
    signals: Mapped[list["Signal"]] = relationship(back_populates="ticker", cascade="all, delete-orphan")
    positions: Mapped[list["Position"]] = relationship(back_populates="ticker", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="ticker", cascade="all, delete-orphan")
    fundamentals: Mapped[list["FundamentalSnapshot"]] = relationship(back_populates="ticker", cascade="all, delete-orphan")


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (
        UniqueConstraint("ticker_id", "date", name="uq_prices_ticker_date"),
        Index("idx_prices_ticker_date", "ticker_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    adj_close: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)

    ticker: Mapped["Ticker"] = relationship(back_populates="prices")


class Feature(Base):
    __tablename__ = "features"
    __table_args__ = (
        UniqueConstraint("ticker_id", "date", name="uq_features_ticker_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    rsi_14: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    macd: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    macd_signal: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    volume_zscore: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    ma_20: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    ma_50: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    ma_cross: Mapped[Optional[int]] = mapped_column(SmallInteger)
    momentum_5d: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    momentum_20d: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    bb_pct_b: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    atr_14: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    obv: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    adx_14: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))

    ticker: Mapped["Ticker"] = relationship(back_populates="features")


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_signals_confidence"),
        CheckConstraint("signal IN ('BUY','SELL','HOLD')", name="ck_signals_signal"),
        Index("idx_signals_generated_at", "generated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    signal: Mapped[str] = mapped_column(String(4), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    composite_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)

    ticker: Mapped["Ticker"] = relationship(back_populates="signals")
    orders: Mapped[list["Order"]] = relationship(back_populates="signal")


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (
        Index("idx_positions_open", "mode", "closed_at", postgresql_where="closed_at IS NULL"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    shares: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    mode: Mapped[str] = mapped_column(String(5), nullable=False)

    ticker: Mapped["Ticker"] = relationship(back_populates="positions")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("idx_orders_executed_at", "executed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(100))
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    shares: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    requested_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    filled_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    slippage: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    commission: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reason: Mapped[Optional[str]] = mapped_column(Text)
    signal_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("signals.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(5), nullable=False)

    ticker: Mapped["Ticker"] = relationship(back_populates="orders")
    signal: Mapped[Optional["Signal"]] = relationship(back_populates="orders")


class EquitySnapshot(Base):
    __tablename__ = "equity_snapshots"
    __table_args__ = (
        UniqueConstraint("timestamp", "mode", name="uq_equity_snapshot_ts_mode"),
        Index("idx_equity_snapshots_mode_ts", "mode", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    positions_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_equity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    realized_pnl_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    benchmark_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    mode: Mapped[str] = mapped_column(String(5), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_log_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor: Mapped[Optional[str]] = mapped_column(String(50))
    details: Mapped[dict] = mapped_column(JSON, nullable=False)


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class FundamentalSnapshot(Base):
    __tablename__ = "fundamental_snapshots"
    __table_args__ = (
        UniqueConstraint("ticker_id", name="uq_fundamentals_ticker"),
        Index("idx_fundamentals_ticker_id", "ticker_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    forward_pe: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    analyst_target_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    week_52_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    week_52_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    beta: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(200))

    ticker: Mapped["Ticker"] = relationship(back_populates="fundamentals")
