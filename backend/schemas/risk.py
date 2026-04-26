from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class RiskMetricsOut(BaseModel):
    sharpe_ratio: Optional[Decimal]
    sortino_ratio: Optional[Decimal]
    var_95: Optional[Decimal]
    max_drawdown_pct: Optional[Decimal]
    beta: Optional[Decimal]
    calmar_ratio: Optional[Decimal]
    cagr: Optional[Decimal]
    total_return_pct: Optional[Decimal]
    win_rate: Optional[Decimal]
    avg_trade_duration_days: Optional[Decimal]
    days_computed: int


class KillSwitchState(BaseModel):
    active: bool
    reason: Optional[str] = None
    activated_at: Optional[str] = None


class KillSwitchRequest(BaseModel):
    active: bool
    reason: str
