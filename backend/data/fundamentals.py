import asyncio
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

import structlog
import yfinance as yf
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import FundamentalSnapshot, Ticker

log = structlog.get_logger(__name__)

FUNDAMENTAL_FIELDS = [
    "pe_ratio", "forward_pe", "market_cap", "analyst_target_price",
    "week_52_high", "week_52_low", "beta", "sector", "industry",
]

_YFINANCE_MAP = {
    "pe_ratio":             "trailingPE",
    "forward_pe":           "forwardPE",
    "market_cap":           "marketCap",
    "analyst_target_price": "targetMeanPrice",
    "week_52_high":         "fiftyTwoWeekHigh",
    "week_52_low":          "fiftyTwoWeekLow",
    "beta":                 "beta",
    "sector":               "sector",
    "industry":             "industry",
}

_STRING_MAX = {"sector": 100, "industry": 200}


def _to_decimal(val) -> Optional[Decimal]:
    if val is None:
        return None
    try:
        return Decimal(str(round(float(val), 6)))
    except (InvalidOperation, ValueError, TypeError):
        return None


def fetch_fundamentals(symbol: str) -> dict:
    try:
        info = yf.Ticker(symbol).info
    except Exception as exc:
        log.warning("fundamentals_fetch_failed", symbol=symbol, error=str(exc))
        return {}

    result: dict = {}
    for field, yf_key in _YFINANCE_MAP.items():
        raw = info.get(yf_key)
        if field in _STRING_MAX:
            result[field] = str(raw)[: _STRING_MAX[field]] if raw else None
        else:
            result[field] = _to_decimal(raw)
    return result


async def fetch_and_store_fundamentals(
    session: AsyncSession,
    ticker_symbols: list[str],
) -> int:
    if not ticker_symbols:
        return 0

    result = await session.execute(
        select(Ticker).where(Ticker.symbol.in_(ticker_symbols))
    )
    symbol_to_id = {t.symbol: t.id for t in result.scalars()}

    loop = asyncio.get_event_loop()
    records = []
    now = datetime.now(timezone.utc)

    for symbol in ticker_symbols:
        ticker_id = symbol_to_id.get(symbol)
        if ticker_id is None:
            continue

        data = await loop.run_in_executor(None, fetch_fundamentals, symbol)
        if not data:
            continue

        records.append({"ticker_id": ticker_id, "fetched_at": now, **data})
        await asyncio.sleep(1)

    if not records:
        return 0

    stmt = pg_insert(FundamentalSnapshot).values(records)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_fundamentals_ticker",
        set_={col: getattr(stmt.excluded, col) for col in FUNDAMENTAL_FIELDS + ["fetched_at"]},
    )
    await session.execute(stmt)
    await session.commit()

    log.info("fundamentals_upserted", count=len(records))
    return len(records)
