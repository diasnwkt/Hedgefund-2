from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings, get_settings
from db.models import AppSettings, AuditLog, Ticker
from dependencies import get_current_user, get_db
from schemas.settings import ModeOut, ModeUpdate, WatchlistOut, WatchlistUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/watchlist", response_model=WatchlistOut)
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    result = await db.execute(select(Ticker).where(Ticker.active == True))
    tickers = result.scalars().all()
    symbols = [t.symbol for t in tickers]
    return WatchlistOut(symbols=symbols, count=len(symbols))


@router.post("/watchlist", response_model=WatchlistOut)
async def update_watchlist(
    body: WatchlistUpdate,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    result = await db.execute(select(Ticker))
    all_tickers = {t.symbol: t for t in result.scalars()}

    for symbol in body.symbols:
        if symbol in all_tickers:
            all_tickers[symbol].active = True
        else:
            db.add(Ticker(symbol=symbol, active=True))

    # Deactivate tickers not in new list
    for symbol, ticker in all_tickers.items():
        if symbol not in body.symbols:
            ticker.active = False

    db.add(AuditLog(
        event_type="watchlist_update",
        actor=user,
        details={"symbols": body.symbols},
    ))
    await db.commit()

    return WatchlistOut(symbols=body.symbols, count=len(body.symbols))


@router.get("/mode", response_model=ModeOut)
async def get_mode(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: str = Depends(get_current_user),
):
    result = await db.execute(select(AppSettings).where(AppSettings.key == "trading_mode"))
    row = result.scalars().first()
    mode = row.value if row else settings.trading_mode
    return ModeOut(mode=mode, live_enabled=settings.alpaca_live_enabled)


@router.post("/mode", response_model=ModeOut)
async def update_mode(
    body: ModeUpdate,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: str = Depends(get_current_user),
):
    if body.mode == "live":
        if not settings.alpaca_live_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ALPACA_LIVE_ENABLED must be true in .env and backend must be restarted before enabling live mode.",
            )
        if body.confirm != "I_UNDERSTAND_RISK":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='confirm must be "I_UNDERSTAND_RISK" to switch to live mode.',
            )

    result = await db.execute(select(AppSettings).where(AppSettings.key == "trading_mode"))
    row = result.scalars().first()
    if row:
        old_mode = row.value
        row.value = body.mode
    else:
        old_mode = settings.trading_mode
        db.add(AppSettings(key="trading_mode", value=body.mode))

    db.add(AuditLog(
        event_type="mode_switch",
        actor=user,
        details={"from": old_mode, "to": body.mode, "confirmed": body.confirm},
    ))
    await db.commit()

    return ModeOut(mode=body.mode, live_enabled=settings.alpaca_live_enabled)


@router.get("/audit/log")
async def audit_log(
    event_type: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    from db.models import AuditLog as AL
    query = select(AL).order_by(AL.timestamp.desc()).limit(limit)
    if event_type:
        query = query.where(AL.event_type == event_type)
    result = await db.execute(query)
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "event_type": e.event_type,
            "actor": e.actor,
            "details": e.details,
        }
        for e in entries
    ]
