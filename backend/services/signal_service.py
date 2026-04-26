from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from db.models import Feature, FundamentalSnapshot, Signal, Ticker
from schemas.signals import KeyIndicatorsOut, RankedSignalOut, SignalOut, TodaySignalsOut


def _to_signal_out(s: Signal) -> SignalOut:
    return SignalOut(
        id=s.id,
        symbol=s.ticker.symbol if s.ticker else "unknown",
        generated_at=s.generated_at,
        signal=s.signal,
        confidence=s.confidence,
        model_version=s.model_version,
        executed=s.executed,
        rationale=s.rationale,
        composite_score=s.composite_score,
    )


async def get_signals_today(session: AsyncSession) -> TodaySignalsOut:
    today = datetime.now(timezone.utc).date()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    result = await session.execute(
        select(Signal)
        .options(joinedload(Signal.ticker))
        .where(Signal.generated_at >= start)
        .order_by(Signal.generated_at.desc())
    )
    signals = result.unique().scalars().all()

    out = [_to_signal_out(s) for s in signals]
    executed_count = sum(1 for s in signals if s.executed)
    return TodaySignalsOut(
        signals=out,
        generated_count=len(out),
        executed_count=executed_count,
        date=today.isoformat(),
    )


async def get_signals_history(
    session: AsyncSession,
    limit: int = 100,
    symbol: str | None = None,
) -> list[SignalOut]:
    query = (
        select(Signal)
        .options(joinedload(Signal.ticker))
        .order_by(Signal.generated_at.desc())
        .limit(limit)
    )

    if symbol:
        ticker_result = await session.execute(
            select(Ticker).where(Ticker.symbol == symbol.upper())
        )
        ticker = ticker_result.scalars().first()
        if ticker:
            query = query.where(Signal.ticker_id == ticker.id)
        else:
            return []

    result = await session.execute(query)
    signals = result.unique().scalars().all()
    return [_to_signal_out(s) for s in signals]


async def get_ranked_signals(
    session: AsyncSession,
    limit: int = 20,
) -> list[RankedSignalOut]:
    today = datetime.now(timezone.utc).date()
    start_dt = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    # Subquery: latest feature date per ticker
    latest_feat_sq = (
        select(Feature.ticker_id, func.max(Feature.date).label("max_date"))
        .group_by(Feature.ticker_id)
        .subquery()
    )

    stmt = (
        select(Signal, Ticker, Feature, FundamentalSnapshot)
        .join(Ticker, Signal.ticker_id == Ticker.id)
        .join(latest_feat_sq, latest_feat_sq.c.ticker_id == Signal.ticker_id)
        .join(
            Feature,
            and_(
                Feature.ticker_id == Signal.ticker_id,
                Feature.date == latest_feat_sq.c.max_date,
            ),
        )
        .outerjoin(FundamentalSnapshot, FundamentalSnapshot.ticker_id == Signal.ticker_id)
        .where(
            Signal.generated_at >= start_dt,
            Signal.signal == "BUY",
            Signal.composite_score.is_not(None),
        )
        .order_by(desc(Signal.composite_score))
        .limit(limit)
    )

    rows = (await session.execute(stmt)).all()

    results = []
    for signal, ticker, feature, fund in rows:
        macd_trend = None
        if feature.macd is not None and feature.macd_signal is not None:
            macd_trend = "bullish" if float(feature.macd) > float(feature.macd_signal) else "bearish"

        ki = KeyIndicatorsOut(
            rsi_14=feature.rsi_14,
            macd_trend=macd_trend,
            bb_pct_b=feature.bb_pct_b,
            adx_14=feature.adx_14,
            momentum_20d=feature.momentum_20d,
        )

        results.append(RankedSignalOut(
            id=signal.id,
            symbol=ticker.symbol,
            signal=signal.signal,
            confidence=signal.confidence,
            composite_score=signal.composite_score,
            rationale=signal.rationale,
            model_version=signal.model_version,
            generated_at=signal.generated_at,
            executed=signal.executed,
            pe_ratio=fund.pe_ratio if fund else None,
            forward_pe=fund.forward_pe if fund else None,
            analyst_target_price=fund.analyst_target_price if fund else None,
            week_52_high=fund.week_52_high if fund else None,
            week_52_low=fund.week_52_low if fund else None,
            beta=fund.beta if fund else None,
            sector=fund.sector if fund else None,
            key_indicators=ki,
        ))

    return results
