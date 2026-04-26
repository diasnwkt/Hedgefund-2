from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from broker.base import BaseBroker
from config import Settings
from db.models import AppSettings, AuditLog, EquitySnapshot, Order, Position, Ticker
from risk.limits import PreTradeChecker

log = structlog.get_logger(__name__)


class PortfolioManager:
    def __init__(self, session: AsyncSession, broker: BaseBroker, settings: Settings) -> None:
        self.session = session
        self.broker = broker
        self.settings = settings

    async def _get_cash(self) -> Decimal:
        result = await self.session.execute(
            select(AppSettings).where(AppSettings.key == "cash")
        )
        row = result.scalars().first()
        if row is None:
            return Decimal(str(self.settings.paper_initial_cash))
        return Decimal(row.value)

    async def _set_cash(self, cash: Decimal) -> None:
        result = await self.session.execute(
            select(AppSettings).where(AppSettings.key == "cash")
        )
        row = result.scalars().first()
        if row is None:
            self.session.add(AppSettings(key="cash", value=str(cash)))
        else:
            row.value = str(cash)

    async def get_open_positions(self) -> list[Position]:
        result = await self.session.execute(
            select(Position).where(Position.closed_at.is_(None))
        )
        return result.scalars().all()

    async def get_position_for_ticker(self, ticker_id: int) -> Optional[Position]:
        result = await self.session.execute(
            select(Position).where(
                Position.ticker_id == ticker_id,
                Position.closed_at.is_(None),
            )
        )
        return result.scalars().first()

    async def execute_signal(
        self,
        ticker: Ticker,
        signal_str: str,
        confidence: float,
        current_price: Decimal,
        signal_id: Optional[int],
        mode: str,
    ) -> Optional[Order]:
        checker = PreTradeChecker(self.session, self.settings)
        cash = await self._get_cash()
        open_positions = await self.get_open_positions()
        total_equity = cash + sum(
            pos.shares * current_price for pos in open_positions
        )

        if signal_str == "BUY":
            max_position_value = total_equity * Decimal(str(self.settings.max_position_size_pct))
            shares = (max_position_value / current_price).quantize(Decimal("0.000001"))
            cost = shares * current_price + Decimal(str(self.settings.paper_commission_usd))

            if cost > cash:
                shares = ((cash - Decimal(str(self.settings.paper_commission_usd))) / current_price).quantize(Decimal("0.000001"))
                if shares <= 0:
                    log.warning("insufficient_cash_for_buy", symbol=ticker.symbol, cash=str(cash))
                    return None

            check = await checker.check_all(
                ticker=ticker,
                side="buy",
                shares=shares,
                price=current_price,
                cash=cash,
                open_positions=open_positions,
                total_equity=total_equity,
            )
            if not check.approved:
                log.warning("pre_trade_check_rejected", symbol=ticker.symbol, reason=check.reason)
                await self._write_audit("order", "system", {
                    "symbol": ticker.symbol,
                    "side": "buy",
                    "reason": check.reason,
                    "status": "rejected",
                })
                return None

            order_result = await self.broker.submit_buy(ticker.symbol, shares, current_price, signal_id)

        elif signal_str == "SELL":
            position = await self.get_position_for_ticker(ticker.ticker_id if hasattr(ticker, "ticker_id") else ticker.id)
            if position is None:
                log.info("no_position_to_sell", symbol=ticker.symbol)
                return None
            shares = position.shares

            check = await checker.check_all(
                ticker=ticker,
                side="sell",
                shares=shares,
                price=current_price,
                cash=cash,
                open_positions=open_positions,
                total_equity=total_equity,
            )
            if not check.approved:
                log.warning("pre_trade_check_rejected", symbol=ticker.symbol, reason=check.reason)
                return None

            order_result = await self.broker.submit_sell(ticker.symbol, shares, current_price, signal_id)
        else:
            return None

        now = datetime.now(timezone.utc)
        order = Order(
            external_id=order_result.external_id,
            ticker_id=ticker.id,
            side=order_result.side,
            shares=order_result.shares,
            requested_price=current_price,
            filled_price=order_result.filled_price,
            slippage=order_result.slippage,
            commission=order_result.commission,
            status=order_result.status,
            reason=order_result.reason,
            signal_id=signal_id,
            submitted_at=now,
            executed_at=now if order_result.status == "filled" else None,
            mode=mode,
        )
        self.session.add(order)

        if order_result.status == "filled" and order_result.filled_price:
            await self._update_position(ticker, order_result, mode, now)

        await self._write_audit("order", "system", {
            "symbol": ticker.symbol,
            "side": order_result.side,
            "shares": str(order_result.shares),
            "fill_price": str(order_result.filled_price),
            "status": order_result.status,
        })
        log.info(
            "order_recorded",
            symbol=ticker.symbol,
            side=order_result.side,
            shares=str(shares),
            status=order_result.status,
        )
        return order

    async def _update_position(self, ticker: Ticker, order_result, mode: str, now: datetime) -> None:
        fill_price = order_result.filled_price
        shares = order_result.shares
        commission = order_result.commission

        if order_result.side == "buy":
            existing = await self.get_position_for_ticker(ticker.id)
            if existing:
                total_cost = existing.avg_cost * existing.shares + fill_price * shares
                total_shares = existing.shares + shares
                existing.avg_cost = (total_cost / total_shares).quantize(Decimal("0.0001"))
                existing.shares = total_shares
            else:
                position = Position(
                    ticker_id=ticker.id,
                    shares=shares,
                    avg_cost=fill_price,
                    opened_at=now,
                    mode=mode,
                )
                self.session.add(position)

            cash = await self._get_cash()
            await self._set_cash(cash - shares * fill_price - commission)

        elif order_result.side == "sell":
            existing = await self.get_position_for_ticker(ticker.id)
            if existing:
                realized = (fill_price - existing.avg_cost) * shares - commission
                existing.realized_pnl += realized
                existing.shares -= shares
                if existing.shares <= Decimal("0.000001"):
                    existing.closed_at = now
                    existing.shares = Decimal("0")

            cash = await self._get_cash()
            await self._set_cash(cash + shares * fill_price - commission)

    async def snapshot_equity(self, current_prices: dict[str, Decimal], mode: str) -> EquitySnapshot:
        cash = await self._get_cash()
        open_positions = await self.get_open_positions()

        positions_value = Decimal("0")
        for pos in open_positions:
            result = await self.session.execute(select(Ticker).where(Ticker.id == pos.ticker_id))
            ticker = result.scalars().first()
            if ticker and ticker.symbol in current_prices:
                positions_value += pos.shares * current_prices[ticker.symbol]

        realized_pnl_total = sum(
            (p.realized_pnl for p in open_positions), Decimal("0")
        )

        snapshot = EquitySnapshot(
            timestamp=datetime.now(timezone.utc),
            cash=cash,
            positions_value=positions_value,
            total_equity=cash + positions_value,
            realized_pnl_total=realized_pnl_total,
            mode=mode,
        )
        self.session.add(snapshot)
        return snapshot

    async def _write_audit(self, event_type: str, actor: str, details: dict) -> None:
        log_entry = AuditLog(
            event_type=event_type,
            actor=actor,
            details=details,
        )
        self.session.add(log_entry)
