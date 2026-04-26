from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AppSettings, EquitySnapshot, Position, Ticker
from dependencies import get_current_user, get_db
from schemas.portfolio import ClosedPositionOut, EquityHistoryOut, EquityPoint, PortfolioSummary, PositionOut
from services.portfolio_service import (
    get_closed_positions,
    get_equity_history,
    get_open_positions_with_prices,
    get_portfolio_summary,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    return await get_portfolio_summary(db)


@router.get("/positions", response_model=list[PositionOut])
async def open_positions(
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    return await get_open_positions_with_prices(db)


@router.get("/history", response_model=list[ClosedPositionOut])
async def closed_positions(
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    return await get_closed_positions(db)


@router.get("/equity/history", response_model=EquityHistoryOut)
async def equity_history(
    days: int = Query(default=90, ge=1, le=1825),
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    return await get_equity_history(db, days=days)


@router.get("/equity/benchmark", response_model=EquityHistoryOut)
async def equity_benchmark(
    days: int = Query(default=90, ge=1, le=1825),
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    return await get_equity_history(db, days=days, include_benchmark=True)
