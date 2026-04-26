from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    shares: Decimal
    avg_cost: Decimal
    current_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_pct: Optional[Decimal] = None
    opened_at: datetime
    mode: str


class ClosedPositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    shares: Decimal
    avg_cost: Decimal
    realized_pnl: Decimal
    opened_at: datetime
    closed_at: Optional[datetime]
    mode: str


class PortfolioSummary(BaseModel):
    cash: Decimal
    positions_value: Decimal
    total_equity: Decimal
    total_return_pct: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    mode: str
    peak_equity: Decimal
    current_drawdown_pct: Decimal


class EquityPoint(BaseModel):
    timestamp: datetime
    total_equity: Decimal
    cash: Decimal
    positions_value: Decimal
    realized_pnl_total: Decimal
    benchmark_value: Optional[Decimal] = None


class EquityHistoryOut(BaseModel):
    points: list[EquityPoint]
    initial_equity: Decimal
