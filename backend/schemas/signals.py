from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    generated_at: datetime
    signal: Literal["BUY", "SELL", "HOLD"]
    confidence: Decimal
    model_version: str
    executed: bool
    rationale: Optional[str] = None
    composite_score: Optional[Decimal] = None


class SignalHistoryParams(BaseModel):
    limit: int = 100
    symbol: Optional[str] = None


class TodaySignalsOut(BaseModel):
    signals: list[SignalOut]
    generated_count: int
    executed_count: int
    date: str


class KeyIndicatorsOut(BaseModel):
    rsi_14: Optional[Decimal] = None
    macd_trend: Optional[str] = None
    bb_pct_b: Optional[Decimal] = None
    adx_14: Optional[Decimal] = None
    momentum_20d: Optional[Decimal] = None


class RankedSignalOut(BaseModel):
    id: int
    symbol: str
    signal: Literal["BUY", "SELL", "HOLD"]
    confidence: Decimal
    composite_score: Optional[Decimal] = None
    rationale: Optional[str] = None
    model_version: str
    generated_at: datetime
    executed: bool

    pe_ratio: Optional[Decimal] = None
    forward_pe: Optional[Decimal] = None
    analyst_target_price: Optional[Decimal] = None
    week_52_high: Optional[Decimal] = None
    week_52_low: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    sector: Optional[str] = None

    key_indicators: KeyIndicatorsOut = KeyIndicatorsOut()
