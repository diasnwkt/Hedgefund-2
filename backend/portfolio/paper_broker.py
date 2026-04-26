from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from broker.base import BaseBroker, OrderResult
from config import Settings

log = structlog.get_logger(__name__)


class PaperBroker(BaseBroker):
    def __init__(self, settings: Settings, current_prices: dict[str, Decimal]) -> None:
        self._settings = settings
        self._current_prices = current_prices

    def _apply_slippage(self, price: Decimal, side: str) -> Decimal:
        slippage_mult = Decimal(str(self._settings.paper_slippage_pct))
        if side == "buy":
            return price * (1 + slippage_mult)
        return price * (1 - slippage_mult)

    async def get_current_price(self, symbol: str) -> Decimal:
        if symbol not in self._current_prices:
            raise ValueError(f"No current price for {symbol}")
        return self._current_prices[symbol]

    async def get_account_cash(self) -> Decimal:
        raise NotImplementedError("Use PortfolioManager for cash tracking in paper mode")

    async def submit_buy(
        self,
        symbol: str,
        shares: Decimal,
        current_price: Decimal,
        signal_id: Optional[int] = None,
    ) -> OrderResult:
        fill_price = self._apply_slippage(current_price, "buy")
        slippage = fill_price - current_price
        commission = Decimal(str(self._settings.paper_commission_usd))

        log.info(
            "paper_buy_filled",
            symbol=symbol,
            shares=str(shares),
            fill_price=str(fill_price),
            slippage=str(slippage),
        )
        return OrderResult(
            external_id=None,
            symbol=symbol,
            side="buy",
            shares=shares,
            filled_price=fill_price,
            slippage=slippage,
            commission=commission,
            status="filled",
        )

    async def submit_sell(
        self,
        symbol: str,
        shares: Decimal,
        current_price: Decimal,
        signal_id: Optional[int] = None,
    ) -> OrderResult:
        fill_price = self._apply_slippage(current_price, "sell")
        slippage = current_price - fill_price
        commission = Decimal(str(self._settings.paper_commission_usd))

        log.info(
            "paper_sell_filled",
            symbol=symbol,
            shares=str(shares),
            fill_price=str(fill_price),
            slippage=str(slippage),
        )
        return OrderResult(
            external_id=None,
            symbol=symbol,
            side="sell",
            shares=shares,
            filled_price=fill_price,
            slippage=slippage,
            commission=commission,
            status="filled",
        )
