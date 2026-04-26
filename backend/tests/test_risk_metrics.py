import numpy as np
import pandas as pd
import pytest

from risk.metrics import (
    sharpe_ratio,
    sortino_ratio,
    var_historical,
    max_drawdown,
    cagr,
    beta,
    calmar_ratio,
    compute_all_metrics,
)


def make_returns(n: int = 252, mean: float = 0.0005, std: float = 0.01, seed: int = 42) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(mean, std, n))


def make_equity(n: int = 252, seed: int = 42) -> pd.Series:
    returns = make_returns(n, seed=seed)
    equity = (1 + returns).cumprod() * 100_000
    return equity


def test_sharpe_positive_drift():
    returns = make_returns(mean=0.001)
    result = sharpe_ratio(returns)
    assert result is not None
    assert result > 0


def test_sharpe_none_insufficient_data():
    assert sharpe_ratio(pd.Series([0.01] * 10)) is None


def test_sortino_finite():
    returns = make_returns()
    result = sortino_ratio(returns)
    assert result is not None
    assert np.isfinite(result)


def test_var_negative():
    returns = make_returns()
    result = var_historical(returns)
    assert result is not None
    assert result < 0


def test_max_drawdown_negative():
    equity = make_equity()
    dd = max_drawdown(equity)
    assert dd <= 0


def test_max_drawdown_flat_is_zero():
    equity = pd.Series([100.0] * 50)
    assert max_drawdown(equity) == 0.0


def test_cagr_positive_drift():
    equity = make_equity(mean=0.001)
    result = cagr(equity)
    assert result is not None
    assert result > 0


def test_beta_correlated():
    returns = make_returns()
    bench = returns + make_returns(std=0.001)
    result = beta(returns, bench)
    assert result is not None
    assert result > 0


def test_compute_all_metrics_returns_dict():
    equity = make_equity()
    metrics = compute_all_metrics(equity)
    assert "sharpe_ratio" in metrics
    assert "max_drawdown_pct" in metrics
    assert metrics["days_computed"] == len(equity)


def test_compute_all_metrics_empty_equity():
    metrics = compute_all_metrics(pd.Series(dtype=float))
    assert metrics["days_computed"] == 0
    assert metrics["sharpe_ratio"] is None
