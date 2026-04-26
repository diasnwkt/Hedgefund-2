from decimal import Decimal

import pytest

from config import get_settings
from portfolio.paper_broker import PaperBroker


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def prices():
    return {"AAPL": Decimal("150.00"), "MSFT": Decimal("300.00")}


@pytest.fixture
def broker(settings, prices):
    return PaperBroker(settings, prices)


@pytest.mark.asyncio
async def test_buy_applies_slippage(broker, settings):
    result = await broker.submit_buy("AAPL", Decimal("10"), Decimal("150.00"))
    assert result.status == "filled"
    expected_fill = Decimal("150.00") * (1 + Decimal(str(settings.paper_slippage_pct)))
    assert result.filled_price == expected_fill
    assert result.slippage > 0


@pytest.mark.asyncio
async def test_sell_applies_slippage(broker, settings):
    result = await broker.submit_sell("AAPL", Decimal("10"), Decimal("150.00"))
    assert result.status == "filled"
    expected_fill = Decimal("150.00") * (1 - Decimal(str(settings.paper_slippage_pct)))
    assert result.filled_price == expected_fill
    assert result.slippage > 0


@pytest.mark.asyncio
async def test_commission_applied(broker, settings):
    result = await broker.submit_buy("AAPL", Decimal("10"), Decimal("150.00"))
    assert result.commission == Decimal(str(settings.paper_commission_usd))


@pytest.mark.asyncio
async def test_get_current_price(broker):
    price = await broker.get_current_price("AAPL")
    assert price == Decimal("150.00")


@pytest.mark.asyncio
async def test_unknown_symbol_raises(broker):
    with pytest.raises(ValueError):
        await broker.get_current_price("UNKNOWN")


@pytest.mark.asyncio
async def test_buy_fill_higher_than_ask(broker):
    result = await broker.submit_buy("AAPL", Decimal("5"), Decimal("150.00"))
    assert result.filled_price > Decimal("150.00")


@pytest.mark.asyncio
async def test_sell_fill_lower_than_bid(broker):
    result = await broker.submit_sell("AAPL", Decimal("5"), Decimal("150.00"))
    assert result.filled_price < Decimal("150.00")
