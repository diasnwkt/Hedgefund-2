"""
Integration test: full paper-trading flow.
fetch prices → compute features → generate signal (mocked model) → execute order → snapshot equity
"""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
import pytest_asyncio

from config import get_settings
from db.models import AppSettings, EquitySnapshot, Order, Position, Signal
from portfolio.manager import PortfolioManager
from portfolio.paper_broker import PaperBroker
from sqlalchemy import select
from strategies.base import SignalResult


@pytest_asyncio.fixture
async def seeded_session(session, sample_ticker, sample_prices):
    session.add(AppSettings(key="cash", value="100000.00"))
    session.add(AppSettings(key="trading_mode", value="paper"))
    await session.commit()
    return session


@pytest.mark.asyncio
async def test_full_paper_trading_flow(seeded_session, sample_ticker):
    settings = get_settings()
    current_price = Decimal("155.00")
    prices = {sample_ticker.symbol: current_price}

    broker = PaperBroker(settings, prices)
    manager = PortfolioManager(seeded_session, broker, settings)

    # Simulate BUY signal
    now = datetime.now(timezone.utc)
    sig = Signal(
        ticker_id=sample_ticker.id,
        generated_at=now,
        signal="BUY",
        confidence=Decimal("0.75"),
        model_version="xgb_test",
        executed=False,
    )
    seeded_session.add(sig)
    await seeded_session.commit()

    order = await manager.execute_signal(
        ticker=sample_ticker,
        signal_str="BUY",
        confidence=0.75,
        current_price=current_price,
        signal_id=sig.id,
        mode="paper",
    )

    assert order is not None
    assert order.status == "filled"
    assert order.side == "buy"

    # Verify position created
    positions = await manager.get_open_positions()
    assert len(positions) == 1
    pos = positions[0]
    assert pos.ticker_id == sample_ticker.id
    assert pos.shares > 0

    # Verify cash decreased
    cash = await manager._get_cash()
    assert cash < Decimal("100000.00")

    # Snapshot equity
    snapshot = await manager.snapshot_equity(prices, "paper")
    assert snapshot.total_equity > Decimal("0")
    assert snapshot.cash == cash
    assert snapshot.positions_value > Decimal("0")


@pytest.mark.asyncio
async def test_sell_closes_position(seeded_session, sample_ticker):
    settings = get_settings()
    current_price = Decimal("155.00")
    prices = {sample_ticker.symbol: current_price}

    broker = PaperBroker(settings, prices)
    manager = PortfolioManager(seeded_session, broker, settings)

    # Buy first
    await manager.execute_signal(sample_ticker, "BUY", 0.75, current_price, None, "paper")

    positions_before = await manager.get_open_positions()
    assert len(positions_before) == 1

    # Now sell
    sell_price = Decimal("160.00")
    prices_sell = {sample_ticker.symbol: sell_price}
    broker_sell = PaperBroker(settings, prices_sell)
    manager_sell = PortfolioManager(seeded_session, broker_sell, settings)

    await manager_sell.execute_signal(sample_ticker, "SELL", 0.80, sell_price, None, "paper")

    # Position should be closed
    result = await seeded_session.execute(
        select(Position).where(Position.ticker_id == sample_ticker.id)
    )
    pos = result.scalars().first()
    assert pos is not None
    assert pos.closed_at is not None


@pytest.mark.asyncio
async def test_hold_signal_does_nothing(seeded_session, sample_ticker):
    settings = get_settings()
    prices = {sample_ticker.symbol: Decimal("150.00")}
    broker = PaperBroker(settings, prices)
    manager = PortfolioManager(seeded_session, broker, settings)

    order = await manager.execute_signal(sample_ticker, "HOLD", 0.50, Decimal("150.00"), None, "paper")
    assert order is None
