import time
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import pandas as pd
import structlog
import yfinance as yf
from sqlalchemy import select, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Price, Ticker

log = structlog.get_logger(__name__)


def _validate_ohlcv(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    before = len(df)
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    df = df[df["High"] >= df["Low"]]
    df = df[df["High"] >= df["Open"]]
    df = df[df["High"] >= df["Close"]]
    df = df[df["Volume"] >= 0]
    dropped = before - len(df)
    if dropped:
        log.warning("ohlcv_validation_dropped_rows", symbol=symbol, dropped=dropped)
    return df


def _fetch_with_retry(
    symbols: list[str],
    start: date,
    end: date,
    retry_attempts: int = 3,
    backoff_sec: int = 5,
) -> pd.DataFrame:
    for attempt in range(1, retry_attempts + 1):
        try:
            tickers_str = " ".join(symbols)
            df = yf.download(
                tickers_str,
                start=start.isoformat(),
                end=end.isoformat(),
                auto_adjust=True,
                progress=False,
                threads=True,
            )
            return df
        except Exception as exc:
            log.warning("yfinance_fetch_failed", attempt=attempt, error=str(exc), symbols=symbols)
            if attempt < retry_attempts:
                time.sleep(backoff_sec * attempt)
            else:
                raise


async def fetch_and_store_prices(
    session: AsyncSession,
    symbols: list[str],
    start: date,
    end: date,
    batch_size: int = 10,
    retry_attempts: int = 3,
    backoff_sec: int = 5,
) -> dict[str, int]:
    result: dict[str, int] = {}

    # Build symbol->ticker_id map
    rows = await session.execute(select(Ticker).where(Ticker.symbol.in_(symbols), Ticker.active == True))
    tickers = {t.symbol: t.id for t in rows.scalars()}
    missing = [s for s in symbols if s not in tickers]
    if missing:
        log.warning("tickers_not_in_db", missing=missing)

    active_symbols = [s for s in symbols if s in tickers]
    batches = [active_symbols[i : i + batch_size] for i in range(0, len(active_symbols), batch_size)]

    for batch in batches:
        log.info("fetching_prices_batch", symbols=batch, start=str(start), end=str(end))
        try:
            raw = _fetch_with_retry(batch, start, end, retry_attempts, backoff_sec)
        except Exception as exc:
            log.error("fetch_batch_failed", symbols=batch, error=str(exc))
            continue

        if raw.empty:
            log.warning("empty_price_data", symbols=batch)
            continue

        # Handle multi-ticker vs single-ticker response shape
        for symbol in batch:
            try:
                if len(batch) == 1:
                    sym_df = raw.copy()
                else:
                    sym_df = raw.xs(symbol, axis=1, level=1) if symbol in raw.columns.get_level_values(1) else pd.DataFrame()

                if sym_df.empty:
                    log.warning("no_data_for_symbol", symbol=symbol)
                    continue

                sym_df = _validate_ohlcv(sym_df, symbol)
                if sym_df.empty:
                    continue

                records = []
                for idx, row in sym_df.iterrows():
                    price_date = idx.date() if hasattr(idx, "date") else idx
                    records.append({
                        "ticker_id": tickers[symbol],
                        "date": price_date,
                        "open": Decimal(str(round(float(row["Open"]), 4))),
                        "high": Decimal(str(round(float(row["High"]), 4))),
                        "low": Decimal(str(round(float(row["Low"]), 4))),
                        "close": Decimal(str(round(float(row["Close"]), 4))),
                        "adj_close": Decimal(str(round(float(row["Close"]), 4))),
                        "volume": int(row["Volume"]),
                    })

                if records:
                    stmt = pg_insert(Price).values(records)
                    stmt = stmt.on_conflict_do_update(
                        constraint="uq_prices_ticker_date",
                        set_={
                            "open": stmt.excluded.open,
                            "high": stmt.excluded.high,
                            "low": stmt.excluded.low,
                            "close": stmt.excluded.close,
                            "adj_close": stmt.excluded.adj_close,
                            "volume": stmt.excluded.volume,
                        },
                    )
                    await session.execute(stmt)
                    result[symbol] = len(records)
                    log.info("prices_upserted", symbol=symbol, count=len(records))

            except Exception as exc:
                log.error("price_store_failed", symbol=symbol, error=str(exc))

    return result


async def get_recent_prices(
    session: AsyncSession,
    ticker_id: int,
    days: int = 252,
) -> pd.DataFrame:
    cutoff = date.today() - timedelta(days=days)
    result = await session.execute(
        select(Price)
        .where(Price.ticker_id == ticker_id, Price.date >= cutoff)
        .order_by(Price.date.asc())
    )
    prices = result.scalars().all()
    if not prices:
        return pd.DataFrame()

    data = [
        {
            "date": p.date,
            "open": float(p.open),
            "high": float(p.high),
            "low": float(p.low),
            "close": float(p.close),
            "adj_close": float(p.adj_close),
            "volume": p.volume,
        }
        for p in prices
    ]
    df = pd.DataFrame(data).set_index("date")
    df.index = pd.to_datetime(df.index)
    return df
