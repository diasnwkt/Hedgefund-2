import numpy as np
import pandas as pd


FEATURE_COLS = [
    "rsi_14", "macd", "macd_signal", "volume_zscore",
    "ma_20", "ma_50", "ma_cross", "momentum_5d", "momentum_20d",
    "bb_pct_b", "atr_14", "obv", "adx_14",
]

TARGET_FORWARD_DAYS = 5
TARGET_RETURN_THRESHOLD = 0.01


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["Close"] if "Close" in df.columns else df["adj_close"]
    volume = df["Volume"].astype(float) if "Volume" in df.columns else df["volume"].astype(float)

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
    df["ma_cross"] = np.where(
        (ma20 > ma50) & (ma20.shift(1) <= ma50.shift(1)), 1,
        np.where((ma20 < ma50) & (ma20.shift(1) >= ma50.shift(1)), -1, 0),
    )

    df["momentum_5d"] = close.pct_change(5)
    df["momentum_20d"] = close.pct_change(20)

    high = df["High"] if "High" in df.columns else df["high"]
    low  = df["Low"]  if "Low"  in df.columns else df["low"]

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_range = (bb_upper - bb_lower).replace(0, np.nan)
    df["bb_pct_b"] = (close - bb_lower) / bb_range

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr_14"] = tr.ewm(com=13, min_periods=14).mean()

    df["obv"] = (np.sign(close.diff()).fillna(0) * volume).cumsum()

    up_move   = high.diff()
    down_move = -low.diff()
    plus_dm   = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm  = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr14     = df["atr_14"]
    plus_di   = 100 * plus_dm.ewm(com=13, min_periods=14).mean() / atr14.replace(0, np.nan)
    minus_di  = 100 * minus_dm.ewm(com=13, min_periods=14).mean() / atr14.replace(0, np.nan)
    di_sum    = (plus_di + minus_di).replace(0, np.nan)
    dx        = 100 * (plus_di - minus_di).abs() / di_sum
    df["adx_14"] = dx.ewm(com=13, min_periods=14).mean()

    return df


def make_labels(df: pd.DataFrame, forward_days: int = TARGET_FORWARD_DAYS, threshold: float = TARGET_RETURN_THRESHOLD) -> pd.Series:
    close = df["Close"] if "Close" in df.columns else df["adj_close"]
    fwd_return = close.shift(-forward_days) / close - 1
    return (fwd_return >= threshold).astype(int)


def prepare_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    df = engineer_features(df)
    labels = make_labels(df)
    X = df[FEATURE_COLS].copy()
    valid = X.notna().all(axis=1) & labels.notna()
    X = X[valid].copy()
    y = labels[valid].copy()
    return X, y
