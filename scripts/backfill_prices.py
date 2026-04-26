"""
Backfill historical OHLCV data for all active tickers.
Usage: python scripts/backfill_prices.py [--years 5]
"""
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import get_settings
from data.fetcher import fetch_and_store_prices
from db.models import Ticker


async def main() -> None:
    settings = get_settings()

    years = settings.historical_backfill_years
    if "--years" in sys.argv:
        idx = sys.argv.index("--years")
        years = int(sys.argv[idx + 1])

    end = date.today()
    start = end - timedelta(days=years * 365)
    print(f"Backfilling {start} → {end} ({years} years)")

    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Ticker).where(Ticker.active == True))
        symbols = [t.symbol for t in result.scalars()]
        print(f"Active tickers: {symbols}")

        counts = await fetch_and_store_prices(
            session,
            symbols,
            start,
            end,
            batch_size=settings.yfinance_batch_size,
            retry_attempts=settings.yfinance_retry_attempts,
            backoff_sec=settings.yfinance_retry_backoff_sec,
        )
        await session.commit()

    for sym, count in counts.items():
        print(f"  {sym}: {count} rows upserted")

    print("Backfill complete.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
