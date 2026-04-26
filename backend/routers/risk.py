from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AuditLog
from dependencies import get_current_user, get_db, get_redis
from risk.limits import KILLSWITCH_REASON_KEY, KILLSWITCH_REDIS_KEY, KILLSWITCH_TS_KEY
from schemas.risk import KillSwitchRequest, KillSwitchState, RiskMetricsOut
from services.portfolio_service import get_equity_history
from risk.metrics import compute_all_metrics
import pandas as pd

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/metrics", response_model=RiskMetricsOut)
async def risk_metrics(
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    equity_data = await get_equity_history(db, days=365)
    if not equity_data.points:
        return RiskMetricsOut(
            sharpe_ratio=None, sortino_ratio=None, var_95=None, max_drawdown_pct=None,
            beta=None, calmar_ratio=None, cagr=None, total_return_pct=None,
            win_rate=None, avg_trade_duration_days=None, days_computed=0,
        )

    equities = pd.Series([float(p.total_equity) for p in equity_data.points])
    bench = pd.Series([float(p.benchmark_value) for p in equity_data.points if p.benchmark_value])

    metrics = compute_all_metrics(equities, bench if not bench.empty else None)

    def to_decimal(v):
        if v is None:
            return None
        from decimal import Decimal
        return Decimal(str(round(v, 6)))

    return RiskMetricsOut(
        sharpe_ratio=to_decimal(metrics.get("sharpe_ratio")),
        sortino_ratio=to_decimal(metrics.get("sortino_ratio")),
        var_95=to_decimal(metrics.get("var_95")),
        max_drawdown_pct=to_decimal(metrics.get("max_drawdown_pct")),
        beta=to_decimal(metrics.get("beta")),
        calmar_ratio=to_decimal(metrics.get("calmar_ratio")),
        cagr=to_decimal(metrics.get("cagr")),
        total_return_pct=to_decimal(metrics.get("total_return_pct")),
        win_rate=None,
        avg_trade_duration_days=None,
        days_computed=metrics.get("days_computed", 0),
    )


@router.get("/killswitch", response_model=KillSwitchState)
async def get_killswitch(
    redis=Depends(get_redis),
    user: str = Depends(get_current_user),
):
    active_val = await redis.get(KILLSWITCH_REDIS_KEY)
    reason = await redis.get(KILLSWITCH_REASON_KEY)
    ts = await redis.get(KILLSWITCH_TS_KEY)
    active = active_val is not None and active_val.lower() == "true"
    return KillSwitchState(active=active, reason=reason, activated_at=ts)


@router.post("/killswitch", response_model=KillSwitchState)
async def set_killswitch(
    body: KillSwitchRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    user: str = Depends(get_current_user),
):
    now = datetime.now(timezone.utc).isoformat()
    await redis.set(KILLSWITCH_REDIS_KEY, str(body.active).lower())
    await redis.set(KILLSWITCH_REASON_KEY, body.reason)
    await redis.set(KILLSWITCH_TS_KEY, now)

    db.add(AuditLog(
        event_type="killswitch",
        actor=user,
        details={"active": body.active, "reason": body.reason},
    ))
    await db.commit()

    return KillSwitchState(active=body.active, reason=body.reason, activated_at=now)
