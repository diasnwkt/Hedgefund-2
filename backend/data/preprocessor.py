from datetime import date
from decimal import Decimal
from typing import Optional

import numpy as np
import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Feature, Price, Ticker

log = structlog.get_logger(__name__)

FEATURE_COLUMNS = [
    "rsi_14", "macd", "macd_signal", "volume_zscore",
    "ma_20", "ma_50", "ma_cross", "momentum_5d", "momentum_20d",
    "bb_pct_b", "atr_14", "obv", "adx_14",
]


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series]:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    close = df["adj_close"]
    volume = df["volume"].astype(float)

    df = df.copy()
    df["rsi_14"] = compute_rsi(close)

    macd_line, macd_signal = compute_macd(close)
    df["macd"] = macd_line
    df["macd_signal"] = macd_signal

    vol_mean = volume.rolling(20).mean()
    vol_std = volume.rolling(20).std()
    df["volume_zscore"] = (volume - vol_mean) / vol_std.replace(0, np.nan)

    df["ma_20"] = close.rolling(20).mean()
    df["ma_50"] = close.rolling(50).mean()

    ma20 = df["ma_20"]
    ma50 = df["ma_50"]
    prev_ma20 = ma20.shift(1)
    prev_ma50 = ma50.shift(1)
    cross = np.where(
        (ma20 > ma50) & (prev_ma20 <= prev_ma50), 1,
        np.where((ma20 < ma50) & (prev_ma20 >= prev_ma50), -1, 0),
    )
    df["ma_cross"] = cross

    df["momentum_5d"] = close.pct_change(5)
    df["momentum_20d"] = close.pct_change(20)

    # Bollinger Band %B: position of price within the bands (0=lower, 1=upper)
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_range = (bb_upper - bb_lower).replace(0, np.nan)
    df["bb_pct_b"] = (close - bb_lower) / bb_range

    # ATR(14): average true range — must come before ADX
    high = df["high"]
    low = df["low"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr_14"] = tr.ewm(com=13, min_periods=14).mean()

    # OBV: on-balance volume (cumulative directional volume)
    df["obv"] = (np.sign(close.diff()).fillna(0) * volume).cumsum()

    # ADX(14): average directional index (trend strength 0-100)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index
    )
    atr14 = df["atr_14"]
    plus_di = 100 * plus_dm.ewm(com=13, min_periods=14).mean() / atr14.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(com=13, min_periods=14).mean() / atr14.replace(0, np.nan)
    di_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    df["adx_14"] = dx.ewm(com=13, min_periods=14).mean()

    return df


async def compute_and_store_features(
    session: AsyncSession,
    ticker_id: int,
    lookback_days: int = 300,
) -> int:
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=lookback_days)
    result = await session.execute(
        select(Price)
        .where(Price.ticker_id == ticker_id, Price.date >= cutoff)
        .order_by(Price.date.asc())
    )
    prices = result.scalars().all()
    if len(prices) < 60:
        log.warning("insufficient_prices_for_features", ticker_id=ticker_id, count=len(prices))
        return 0

    data = [
        {
            "date": p.date,
            "open": float(p.open),
            "high": float(p.high),
            "low": float(p.low),
            "close": float(p.close),
            "adj_close": float(p.adj_close),
            "volume": p.volume,
        }
        for p in prices
    ]
    df = pd.DataFrame(data).set_index("date")
    df = compute_features(df)

    # Drop rows where any required feature is NaN (warmup)
    df_clean = df.dropna(subset=FEATURE_COLUMNS)
    if df_clean.empty:
        return 0

    def to_decimal(val) -> Optional[Decimal]:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        return Decimal(str(round(float(val), 6)))

    records = []
    for idx, row in df_clean.iterrows():
        records.append({
            "ticker_id": ticker_id,
            "date": idx if isinstance(idx, date) else idx.date(),
            "rsi_14": to_decimal(row.get("rsi_14")),
            "macd": to_decimal(row.get("macd")),
            "macd_signal": to_decimal(row.get("macd_signal")),
            "volume_zscore": to_decimal(row.get("volume_zscore")),
            "ma_20": to_decimal(row.get("ma_20")),
            "ma_50": to_decimal(row.get("ma_50")),
            "ma_cross": int(row.get("ma_cross", 0)),
            "momentum_5d": to_decimal(row.get("momentum_5d")),
            "momentum_20d": to_decimal(row.get("momentum_20d")),
            "bb_pct_b": to_decimal(row.get("bb_pct_b")),
            "atr_14": to_decimal(row.get("atr_14")),
            "obv": to_decimal(row.get("obv")),
            "adx_14": to_decimal(row.get("adx_14")),
        })

    if records:
        stmt = pg_insert(Feature).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_features_ticker_date",
            set_={col: getattr(stmt.excluded, col) for col in FEATURE_COLUMNS},
        )
        await session.execute(stmt)
        log.info("features_upserted", ticker_id=ticker_id, count=len(records))

    return len(records)
