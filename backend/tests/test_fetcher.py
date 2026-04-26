import pandas as pd
import pytest
from data.fetcher import _validate_ohlcv


def make_df(**overrides) -> pd.DataFrame:
    base = {"Open": [100.0], "High": [105.0], "Low": [98.0], "Close": [102.0], "Volume": [1_000_000]}
    base.update(overrides)
    return pd.DataFrame(base)


def test_valid_row_passes():
    df = make_df()
    result = _validate_ohlcv(df, "TEST")
    assert len(result) == 1


def test_nan_close_dropped():
    df = make_df(Close=[float("nan")])
    result = _validate_ohlcv(df, "TEST")
    assert len(result) == 0


def test_high_less_than_low_dropped():
    df = make_df(High=[90.0], Low=[105.0])
    result = _validate_ohlcv(df, "TEST")
    assert len(result) == 0


def test_negative_volume_dropped():
    df = make_df(Volume=[-1])
    result = _validate_ohlcv(df, "TEST")
    assert len(result) == 0


def test_high_less_than_open_dropped():
    df = make_df(Open=[110.0], High=[105.0])
    result = _validate_ohlcv(df, "TEST")
    assert len(result) == 0


def test_mixed_valid_invalid():
    import numpy as np
    df = pd.DataFrame({
        "Open": [100.0, 200.0],
        "High": [105.0, 190.0],  # second row: high < open → dropped
        "Low": [98.0, 185.0],
        "Close": [102.0, 195.0],
        "Volume": [1_000_000, 500_000],
    })
    result = _validate_ohlcv(df, "TEST")
    assert len(result) == 1
