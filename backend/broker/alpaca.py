from decimal import Decimal
from typing import Optional

import structlog
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from broker.base import BaseBroker, OrderResult
from config import Settings

log = structlog.get_logger(__name__)


class AlpacaBroker(BaseBroker):
    def __init__(self, settings: Settings) -> None:
        if not settings.alpaca_live_enabled:
            raise RuntimeError("Live mode is not enabled. Set ALPACA_LIVE_ENABLED=true.")
        self._settings = settings
        self._trading_client = TradingClient(
            api_key=settings.alpaca_live_api_key,
            secret_key=settings.alpaca_live_secret_key,
            paper=False,
        )
        self._data_client = StockHistoricalDataClient(
            api_key=settings.alpaca_live_api_key,
            secret_key=settings.alpaca_live_secret_key,
        )

    async def get_current_price(self, symbol: str) -> Decimal:
        req = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        quote = self._data_client.get_stock_latest_quote(req)
        ask = quote[symbol].ask_price
        return Decimal(str(ask))

    async def get_account_cash(self) -> Decimal:
        account = self._trading_client.get_account()
        return Decimal(str(account.cash))

    async def submit_buy(
        self,
        symbol: str,
        shares: Decimal,
        current_price: Decimal,
        signal_id: Optional[int] = None,
    ) -> OrderResult:
        req = MarketOrderRequest(
            symbol=symbol,
            qty=float(shares),
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
        try:
            order = self._trading_client.submit_order(req)
            log.info("alpaca_buy_submitted", symbol=symbol, shares=str(shares), order_id=str(order.id))
            return OrderResult(
                external_id=str(order.id),
                symbol=symbol,
                side="buy",
                shares=shares,
                filled_price=None,
                slippage=Decimal("0"),
                commission=Decimal("0"),
                status="pending",
            )
        except Exception as exc:
            log.error("alpaca_buy_failed", symbol=symbol, error=str(exc))
            return OrderResult(
                external_id=None,
                symbol=symbol,
                side="buy",
                shares=shares,
                filled_price=None,
                slippage=Decimal("0"),
                commission=Decimal("0"),
                status="rejected",
                reason=str(exc),
            )

    async def submit_sell(
        self,
        symbol: str,
        shares: Decimal,
        current_price: Decimal,
        signal_id: Optional[int] = None,
    ) -> OrderResult:
        req = MarketOrderRequest(
            symbol=symbol,
            qty=float(shares),
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        try:
            order = self._trading_client.submit_order(req)
            log.info("alpaca_sell_submitted", symbol=symbol, shares=str(shares), order_id=str(order.id))
            return OrderResult(
                external_id=str(order.id),
                symbol=symbol,
                side="sell",
                shares=shares,
                filled_price=None,
                slippage=Decimal("0"),
                commission=Decimal("0"),
                status="pending",
            )
        except Exception as exc:
            log.error("alpaca_sell_failed", symbol=symbol, error=str(exc))
            return OrderResult(
                external_id=None,
                symbol=symbol,
                side="sell",
                shares=shares,
                filled_price=None,
                slippage=Decimal("0"),
                commission=Decimal("0"),
                status="rejected",
                reason=str(exc),
            )
