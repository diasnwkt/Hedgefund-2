import glob
import os
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.models import Feature, Signal, Ticker
from strategies.ml_strategy import XGBoostStrategy
from strategies.ollama_filter import OllamaSignalFilter

log = structlog.get_logger(__name__)


def _compute_technical_score(latest_features: dict) -> float:
    """Returns a 0.0–1.0 bullish score from normalized technical indicators."""
    scores = []

    rsi = latest_features.get("rsi_14")
    if rsi is not None:
        scores.append(float(rsi) / 100.0)

    macd = latest_features.get("macd")
    macd_sig = latest_features.get("macd_signal")
    if macd is not None and macd_sig is not None:
        scores.append(1.0 if float(macd) > float(macd_sig) else 0.0)

    ma_cross = latest_features.get("ma_cross", 0)
    scores.append(0.5 + 0.5 * int(ma_cross))

    mom20 = latest_features.get("momentum_20d")
    if mom20 is not None:
        clipped = max(-0.20, min(0.20, float(mom20)))
        scores.append((clipped + 0.20) / 0.40)

    return sum(scores) / len(scores) if scores else 0.5


def _latest_model_path(model_dir: str) -> str | None:
    pattern = os.path.join(model_dir, "xgb_*.pkl")
    files = sorted(glob.glob(pattern), reverse=True)
    return files[0] if files else None


async def generate_signals_for_all(session: AsyncSession) -> list[dict]:
    settings = get_settings()
    model_path = _latest_model_path(settings.model_dir)
    if model_path is None:
        log.error("no_model_found", model_dir=settings.model_dir)
        return []

    strategy = XGBoostStrategy(
        random_seed=settings.ml_random_seed,
        confidence_threshold=settings.signal_confidence_threshold,
    )
    strategy.load(model_path)

    ollama_filter: Optional[OllamaSignalFilter] = None
    if settings.ollama_enabled:
        ollama_filter = OllamaSignalFilter(
            model_name=settings.ollama_model,
            model_path=settings.ollama_model_path,
            confirm_threshold=settings.ollama_confirm_threshold,
        )
        log.info("llm_filter_enabled", model=settings.ollama_model)

    result = await session.execute(select(Ticker).where(Ticker.active == True))
    tickers = result.scalars().all()

    generated: list[dict] = []
    now = datetime.now(timezone.utc)

    for ticker in tickers:
        feat_rows = await session.execute(
            select(Feature)
            .where(Feature.ticker_id == ticker.id)
            .order_by(Feature.date.desc())
            .limit(300)
        )
        features = feat_rows.scalars().all()
        if not features:
            log.warning("no_features_for_ticker", symbol=ticker.symbol)
            continue

        df = pd.DataFrame([
            {
                "date": f.date,
                "rsi_14": float(f.rsi_14) if f.rsi_14 else None,
                "macd": float(f.macd) if f.macd else None,
                "macd_signal": float(f.macd_signal) if f.macd_signal else None,
                "volume_zscore": float(f.volume_zscore) if f.volume_zscore else None,
                "ma_20": float(f.ma_20) if f.ma_20 else None,
                "ma_50": float(f.ma_50) if f.ma_50 else None,
                "ma_cross": int(f.ma_cross) if f.ma_cross is not None else 0,
                "momentum_5d": float(f.momentum_5d) if f.momentum_5d else None,
                "momentum_20d": float(f.momentum_20d) if f.momentum_20d else None,
            }
            for f in features
        ]).sort_values("date")

        try:
            signal_result = strategy.generate_signal(df, ticker.symbol)
        except Exception as exc:
            log.error("signal_generation_failed", symbol=ticker.symbol, error=str(exc))
            continue

        # Compute latest features dict once (used by both LLM filter and composite score)
        latest = df.iloc[-1].to_dict() if not df.empty else {}

        # Apply Ollama LLM filter if enabled
        if ollama_filter is not None:
            signal_result = await ollama_filter.filter(signal_result, latest)

        # Composite score: 60% ML confidence + 40% technical score
        tech_score = _compute_technical_score(latest)
        composite_score = round(0.6 * signal_result.confidence + 0.4 * tech_score, 4)

        # Check for duplicate signal today
        today = now.date()
        existing = await session.execute(
            select(Signal).where(
                Signal.ticker_id == ticker.id,
                Signal.generated_at >= datetime(today.year, today.month, today.day, tzinfo=timezone.utc),
            )
        )
        if existing.scalars().first():
            log.debug("signal_already_exists_today", symbol=ticker.symbol)
            continue

        from decimal import Decimal
        new_signal = Signal(
            ticker_id=ticker.id,
            generated_at=now,
            signal=signal_result.signal,
            confidence=Decimal(str(round(signal_result.confidence, 4))),
            model_version=signal_result.model_version,
            executed=False,
            rationale=signal_result.rationale or None,
            composite_score=Decimal(str(composite_score)),
        )
        session.add(new_signal)
        generated.append({
            "symbol": ticker.symbol,
            "signal": signal_result.signal,
            "confidence": round(signal_result.confidence, 4),
            "composite_score": composite_score,
            "model_version": signal_result.model_version,
        })
        log.info(
            "signal_generated",
            symbol=ticker.symbol,
            signal=signal_result.signal,
            confidence=round(signal_result.confidence, 4),
        )

    return generated
