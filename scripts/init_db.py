"""
Initialize database: create tables and seed the default watchlist + admin password hash.
Usage: python scripts/init_db.py [--password <plaintext>]
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import get_settings
from db.models import AppSettings, Base, Ticker

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed(session: AsyncSession, settings) -> None:
    # Seed watchlist
    for symbol in settings.watchlist:
        result = await session.execute(select(Ticker).where(Ticker.symbol == symbol))
        if not result.scalars().first():
            session.add(Ticker(symbol=symbol, active=True))
            print(f"  Added ticker: {symbol}")

    # Seed initial cash
    result = await session.execute(select(AppSettings).where(AppSettings.key == "cash"))
    if not result.scalars().first():
        session.add(AppSettings(key="cash", value=str(settings.paper_initial_cash)))
        print(f"  Initial cash: ${settings.paper_initial_cash:,.2f}")

    # Seed trading mode
    result = await session.execute(select(AppSettings).where(AppSettings.key == "trading_mode"))
    if not result.scalars().first():
        session.add(AppSettings(key="trading_mode", value=settings.trading_mode))
        print(f"  Trading mode: {settings.trading_mode}")

    await session.commit()
    print("Seed complete.")


async def main() -> None:
    settings = get_settings()

    # Hash password if needed
    if "--password" in sys.argv:
        idx = sys.argv.index("--password")
        plain = sys.argv[idx + 1]
        hashed = pwd_context.hash(plain)
        print(f"\nAdd this to your .env:\nADMIN_PASSWORD_HASH={hashed}\n")
        return

    if settings.admin_password and not settings.admin_password_hash:
        hashed = pwd_context.hash(settings.admin_password)
        print(f"Hashed password for {settings.admin_username}: {hashed}")
        print("Add ADMIN_PASSWORD_HASH to your .env file.\n")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        await seed(session, settings)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
