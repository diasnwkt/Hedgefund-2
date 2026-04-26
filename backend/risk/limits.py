from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from db.models import Order, Position, Ticker
from exceptions import KillSwitchActiveError

log = structlog.get_logger(__name__)

KILLSWITCH_REDIS_KEY = "killswitch:active"
KILLSWITCH_REASON_KEY = "killswitch:reason"
KILLSWITCH_TS_KEY = "killswitch:activated_at"


@dataclass
class CheckResult:
    approved: bool
    reason: Optional[str] = None


class PreTradeChecker:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def check_killswitch(self, redis_client=None) -> CheckResult:
        if redis_client:
            active = await redis_client.get(KILLSWITCH_REDIS_KEY)
            if active and active.lower() == "true":
                raise KillSwitchActiveError()
        return CheckResult(approved=True)

    async def check_daily_order_count(self, mode: str) -> CheckResult:
        today = date.today()
        start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        count_result = await self.session.execute(
            select(func.count(Order.id)).where(
                Order.submitted_at >= start,
                Order.mode == mode,
                Order.status != "rejected",
            )
        )
        count = count_result.scalar() or 0
        if count >= self.settings.max_orders_per_day:
            return CheckResult(approved=False, reason=f"Max daily orders ({self.settings.max_orders_per_day}) reached: {count}")
        return CheckResult(approved=True)

    async def check_position_size(
        self,
        shares: Decimal,
        price: Decimal,
        total_equity: Decimal,
    ) -> CheckResult:
        order_value = shares * price
        max_allowed = total_equity * Decimal(str(self.settings.max_position_size_pct))
        if order_value > max_allowed:
            return CheckResult(
                approved=False,
                reason=f"Position size ${order_value:.2f} exceeds max ${max_allowed:.2f} ({self.settings.max_position_size_pct*100:.0f}% of equity)",
            )
        return CheckResult(approved=True)

    async def check_volume_liquidity(
        self,
        ticker: Ticker,
        shares: Decimal,
    ) -> CheckResult:
        from db.models import Price
        result = await self.session.execute(
            select(func.avg(Price.volume))
            .where(Price.ticker_id == ticker.id)
            .order_by(Price.date.desc())
            .limit(20)
        )
        avg_vol = result.scalar()
        if avg_vol is None:
            return CheckResult(approved=True)

        max_shares = Decimal(str(avg_vol)) * Decimal(str(self.settings.max_order_volume_pct))
        if shares > max_shares:
            return CheckResult(
                approved=False,
                reason=f"Order size {shares} exceeds {self.settings.max_order_volume_pct*100:.0f}% of avg daily volume ({avg_vol:.0f})",
            )
        return CheckResult(approved=True)

    async def check_wash_trade(self, ticker: Ticker, side: str) -> CheckResult:
        if side != "buy" or not self.settings.feature_wash_trade_check:
            return CheckResult(approved=True)

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.settings.wash_trade_window_days)
        result = await self.session.execute(
            select(Order).where(
                Order.ticker_id == ticker.id,
                Order.side == "sell",
                Order.status == "filled",
                Order.executed_at >= cutoff,
            ).order_by(Order.executed_at.desc()).limit(1)
        )
        recent_sell = result.scalars().first()
        if recent_sell:
            return CheckResult(
                approved=False,
                reason=f"Wash-trade prevention: sold {ticker.symbol} within {self.settings.wash_trade_window_days} days",
            )
        return CheckResult(approved=True)

    async def check_all(
        self,
        ticker: Ticker,
        side: str,
        shares: Decimal,
        price: Decimal,
        cash: Decimal,
        open_positions: list[Position],
        total_equity: Decimal,
        mode: str = "paper",
        redis_client=None,
    ) -> CheckResult:
        checks = [
            await self.check_killswitch(redis_client),
            await self.check_daily_order_count(mode),
            await self.check_position_size(shares, price, total_equity),
            await self.check_volume_liquidity(ticker, shares),
            await self.check_wash_trade(ticker, side),
        ]
        for check in checks:
            if not check.approved:
                log.warning("pre_trade_rejected", symbol=ticker.symbol, reason=check.reason)
                return check
        return CheckResult(approved=True)


async def check_stop_losses(session: AsyncSession, settings: Settings, current_prices: dict[str, Decimal], mode: str) -> list[str]:
    from db.models import Price
    triggered = []

    result = await session.execute(
        select(Position).where(Position.closed_at.is_(None), Position.mode == mode)
    )
    open_positions = result.scalars().all()

    for pos in open_positions:
        ticker_result = await session.execute(select(Ticker).where(Ticker.id == pos.ticker_id))
        ticker = ticker_result.scalars().first()
        if not ticker or ticker.symbol not in current_prices:
            continue

        current = current_prices[ticker.symbol]
        loss_pct = float((current - pos.avg_cost) / pos.avg_cost)

        if loss_pct <= -settings.stop_loss_pct:
            log.warning(
                "stop_loss_triggered",
                symbol=ticker.symbol,
                loss_pct=round(loss_pct * 100, 2),
                threshold=-settings.stop_loss_pct * 100,
            )
            triggered.append(ticker.symbol)

    return triggered


async def check_portfolio_drawdown(
    session: AsyncSession,
    settings: Settings,
    current_equity: Decimal,
    mode: str,
    redis_client=None,
) -> bool:
    from db.models import EquitySnapshot
    result = await session.execute(
        select(func.max(EquitySnapshot.total_equity))
        .where(EquitySnapshot.mode == mode)
    )
    peak = result.scalar()
    if peak is None or peak == 0:
        return False

    drawdown = float((current_equity - Decimal(str(peak))) / Decimal(str(peak)))

    if drawdown <= -settings.portfolio_drawdown_limit:
        log.error(
            "drawdown_killswitch_triggered",
            drawdown_pct=round(drawdown * 100, 2),
            threshold=-settings.portfolio_drawdown_limit * 100,
        )
        if redis_client:
            await redis_client.set(KILLSWITCH_REDIS_KEY, "true")
            await redis_client.set(KILLSWITCH_REASON_KEY, f"Auto kill-switch: drawdown {drawdown*100:.1f}%")
            from datetime import datetime, timezone
            await redis_client.set(KILLSWITCH_TS_KEY, datetime.now(timezone.utc).isoformat())
        return True

    return False
