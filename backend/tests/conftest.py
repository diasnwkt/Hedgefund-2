import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import AsyncGenerator

import fakeredis.aioredis
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import get_settings
from db.models import Base, Ticker, Price
from dependencies import get_current_user, get_db, get_redis
from main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


@pytest_asyncio.fixture(scope="function")
async def redis_client():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def async_client(session, redis_client):
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_redis] = lambda: redis_client
    app.dependency_overrides[get_current_user] = lambda: "dias"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_ticker(session: AsyncSession) -> Ticker:
    ticker = Ticker(symbol="AAPL", name="Apple Inc.", active=True)
    session.add(ticker)
    await session.commit()
    await session.refresh(ticker)
    return ticker


@pytest_asyncio.fixture
async def sample_prices(session: AsyncSession, sample_ticker: Ticker) -> list[Price]:
    import random
    random.seed(42)
    prices = []
    price = 150.0
    for i in range(252):
        d = date(2025, 1, 1)
        from datetime import timedelta
        d = d + timedelta(days=i)
        price = price * (1 + random.gauss(0, 0.01))
        p = Price(
            ticker_id=sample_ticker.id,
            date=d,
            open=Decimal(str(round(price * 0.998, 4))),
            high=Decimal(str(round(price * 1.01, 4))),
            low=Decimal(str(round(price * 0.99, 4))),
            close=Decimal(str(round(price, 4))),
            adj_close=Decimal(str(round(price, 4))),
            volume=random.randint(50_000_000, 100_000_000),
        )
        prices.append(p)
        session.add(p)
    await session.commit()
    return prices
