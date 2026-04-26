from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import yfinance as yf
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.models import AppSettings, EquitySnapshot, Position, Ticker
from schemas.portfolio import (
    ClosedPositionOut,
    EquityHistoryOut,
    EquityPoint,
    PortfolioSummary,
    PositionOut,
)

log = structlog.get_logger(__name__)


async def _get_current_prices(symbols: list[str]) -> dict[str, Decimal]:
    if not symbols:
        return {}
    try:
        tickers_str = " ".join(symbols)
        data = yf.download(tickers_str, period="2d", progress=False, auto_adjust=True)
        prices: dict[str, Decimal] = {}
        for sym in symbols:
            try:
                if len(symbols) == 1:
                    close = float(data["Close"].iloc[-1])
                else:
                    close = float(data["Close"][sym].iloc[-1])
                prices[sym] = Decimal(str(round(close, 4)))
            except Exception:
                pass
        return prices
    except Exception as exc:
        log.error("price_fetch_failed", error=str(exc))
        return {}


async def get_portfolio_summary(session: AsyncSession) -> PortfolioSummary:
    settings = get_settings()

    cash_row = await session.execute(select(AppSettings).where(AppSettings.key == "cash"))
    cash_setting = cash_row.scalars().first()
    cash = Decimal(cash_setting.value) if cash_setting else Decimal(str(settings.paper_initial_cash))

    pos_result = await session.execute(
        select(Position).where(Position.closed_at.is_(None))
    )
    positions = pos_result.scalars().all()

    symbols = []
    ticker_map: dict[int, str] = {}
    for pos in positions:
        t = await session.get(Ticker, pos.ticker_id)
        if t:
            ticker_map[pos.ticker_id] = t.symbol
            symbols.append(t.symbol)

    prices = await _get_current_prices(list(set(symbols)))

    positions_value = Decimal("0")
    unrealized_pnl = Decimal("0")
    realized_pnl = Decimal("0")

    for pos in positions:
        symbol = ticker_map.get(pos.ticker_id, "")
        realized_pnl += pos.realized_pnl
        if symbol in prices:
            mv = pos.shares * prices[symbol]
            positions_value += mv
            unrealized_pnl += mv - pos.shares * pos.avg_cost

    total_equity = cash + positions_value
    initial = Decimal(str(settings.paper_initial_cash))
    total_return_pct = ((total_equity - initial) / initial * 100).quantize(Decimal("0.01")) if initial else Decimal("0")

    # Peak equity
    peak_result = await session.execute(
        select(EquitySnapshot).order_by(EquitySnapshot.total_equity.desc()).limit(1)
    )
    peak_row = peak_result.scalars().first()
    peak_equity = Decimal(str(peak_row.total_equity)) if peak_row else total_equity
    drawdown = ((total_equity - peak_equity) / peak_equity * 100) if peak_equity else Decimal("0")

    mode_row = await session.execute(select(AppSettings).where(AppSettings.key == "trading_mode"))
    mode_setting = mode_row.scalars().first()
    mode = mode_setting.value if mode_setting else settings.trading_mode

    return PortfolioSummary(
        cash=cash,
        positions_value=positions_value,
        total_equity=total_equity,
        total_return_pct=total_return_pct,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        mode=mode,
        peak_equity=peak_equity,
        current_drawdown_pct=drawdown,
    )


async def get_open_positions_with_prices(session: AsyncSession) -> list[PositionOut]:
    pos_result = await session.execute(select(Position).where(Position.closed_at.is_(None)))
    positions = pos_result.scalars().all()

    symbols = []
    ticker_map: dict[int, str] = {}
    for pos in positions:
        t = await session.get(Ticker, pos.ticker_id)
        if t:
            ticker_map[pos.ticker_id] = t.symbol
            symbols.append(t.symbol)

    prices = await _get_current_prices(list(set(symbols)))
    result = []

    for pos in positions:
        symbol = ticker_map.get(pos.ticker_id, "unknown")
        current_price = prices.get(symbol)
        market_value = pos.shares * current_price if current_price else None
        unrealized_pnl = (market_value - pos.shares * pos.avg_cost) if market_value else None
        unrealized_pnl_pct = (unrealized_pnl / (pos.shares * pos.avg_cost) * 100) if unrealized_pnl else None

        result.append(PositionOut(
            id=pos.id,
            symbol=symbol,
            shares=pos.shares,
            avg_cost=pos.avg_cost,
            current_price=current_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            opened_at=pos.opened_at,
            mode=pos.mode,
        ))

    return result


async def get_closed_positions(session: AsyncSession) -> list[ClosedPositionOut]:
    result = await session.execute(
        select(Position).where(Position.closed_at.is_not(None)).order_by(Position.closed_at.desc())
    )
    positions = result.scalars().all()
    out = []
    for pos in positions:
        t = await session.get(Ticker, pos.ticker_id)
        symbol = t.symbol if t else "unknown"
        out.append(ClosedPositionOut(
            id=pos.id,
            symbol=symbol,
            shares=pos.shares,
            avg_cost=pos.avg_cost,
            realized_pnl=pos.realized_pnl,
            opened_at=pos.opened_at,
            closed_at=pos.closed_at,
            mode=pos.mode,
        ))
    return out


async def get_equity_history(
    session: AsyncSession,
    days: int = 90,
    include_benchmark: bool = False,
) -> EquityHistoryOut:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await session.execute(
        select(EquitySnapshot)
        .where(EquitySnapshot.timestamp >= cutoff)
        .order_by(EquitySnapshot.timestamp.asc())
    )
    snapshots = result.scalars().all()

    points = [
        EquityPoint(
            timestamp=s.timestamp,
            total_equity=s.total_equity,
            cash=s.cash,
            positions_value=s.positions_value,
            realized_pnl_total=s.realized_pnl_total,
            benchmark_value=s.benchmark_value if include_benchmark else None,
        )
        for s in snapshots
    ]

    settings = get_settings()
    initial = Decimal(str(settings.paper_initial_cash))
    return EquityHistoryOut(points=points, initial_equity=initial)
