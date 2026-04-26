import numpy as np
import pandas as pd
import pytest

from data.preprocessor import compute_features, compute_rsi, compute_macd, FEATURE_COLUMNS


def make_price_df(n: int = 100, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    prices = 100 + rng.normal(0, 1, n).cumsum()
    volumes = rng.integers(1_000_000, 5_000_000, n)
    return pd.DataFrame({
        "open": prices * 0.999,
        "high": prices * 1.005,
        "low": prices * 0.995,
        "close": prices,
        "adj_close": prices,
        "volume": volumes,
    })


def test_rsi_bounds():
    series = pd.Series(range(1, 51), dtype=float)
    rsi = compute_rsi(series)
    valid = rsi.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_macd_returns_two_series():
    series = pd.Series(range(1, 51), dtype=float)
    macd, signal = compute_macd(series)
    assert len(macd) == len(series)
    assert len(signal) == len(series)


def test_compute_features_columns_present():
    df = make_price_df(100)
    result = compute_features(df)
    for col in FEATURE_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"


def test_compute_features_warmup_is_nan():
    df = make_price_df(100)
    result = compute_features(df)
    # First ~50 rows should have NaN in MA-50 (warmup)
    assert result["ma_50"].iloc[:49].isna().any()


def test_ma_cross_values():
    df = make_price_df(200)
    result = compute_features(df)
    valid = result["ma_cross"].dropna()
    assert set(valid.unique()).issubset({-1, 0, 1})


def test_momentum_5d_matches_pct_change():
    df = make_price_df(100)
    result = compute_features(df)
    expected = df["adj_close"].pct_change(5)
    pd.testing.assert_series_equal(result["momentum_5d"], expected, check_names=False, check_dtype=False)
