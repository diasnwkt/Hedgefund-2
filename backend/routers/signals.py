from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from schemas.signals import RankedSignalOut, SignalOut, TodaySignalsOut
from services.signal_service import get_ranked_signals, get_signals_history, get_signals_today

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/ranked", response_model=list[RankedSignalOut])
async def signals_ranked(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    return await get_ranked_signals(db, limit=limit)


@router.get("/today", response_model=TodaySignalsOut)
async def signals_today(
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    return await get_signals_today(db)


@router.get("/history", response_model=list[SignalOut])
async def signals_history(
    limit: int = Query(default=100, ge=1, le=1000),
    symbol: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    return await get_signals_history(db, limit=limit, symbol=symbol)
