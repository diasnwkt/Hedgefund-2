from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from config import get_settings
from exceptions import KillSwitchActiveError
from risk.limits import KILLSWITCH_REDIS_KEY, PreTradeChecker


@pytest.fixture
def settings():
    return get_settings()


@pytest.mark.asyncio
async def test_killswitch_raises_when_active(session, settings):
    redis = AsyncMock()
    redis.get = AsyncMock(return_value="true")
    checker = PreTradeChecker(session, settings)
    with pytest.raises(KillSwitchActiveError):
        await checker.check_killswitch(redis)


@pytest.mark.asyncio
async def test_killswitch_passes_when_inactive(session, settings):
    redis = AsyncMock()
    redis.get = AsyncMock(return_value="false")
    checker = PreTradeChecker(session, settings)
    result = await checker.check_killswitch(redis)
    assert result.approved


@pytest.mark.asyncio
async def test_position_size_within_limit(session, settings):
    checker = PreTradeChecker(session, settings)
    result = await checker.check_position_size(
        shares=Decimal("10"),
        price=Decimal("100"),
        total_equity=Decimal("100_000"),
    )
    assert result.approved


@pytest.mark.asyncio
async def test_position_size_exceeds_limit(session, settings):
    checker = PreTradeChecker(session, settings)
    result = await checker.check_position_size(
        shares=Decimal("200"),
        price=Decimal("100"),
        total_equity=Decimal("100_000"),
    )
    assert not result.approved
    assert "max" in result.reason.lower() or "exceed" in result.reason.lower()


@pytest.mark.asyncio
async def test_wash_trade_no_prior_sell(session, sample_ticker, settings):
    checker = PreTradeChecker(session, settings)
    result = await checker.check_wash_trade(sample_ticker, "buy")
    assert result.approved


@pytest.mark.asyncio
async def test_daily_order_count_empty(session, settings):
    checker = PreTradeChecker(session, settings)
    result = await checker.check_daily_order_count("paper")
    assert result.approved
