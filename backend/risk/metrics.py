from decimal import Decimal
from typing import Optional

import numpy as np
import pandas as pd


def _annualize(daily_returns: pd.Series, trading_days: int = 252) -> float:
    return float(daily_returns.mean() * trading_days)


def sharpe_ratio(daily_returns: pd.Series, risk_free_rate: float = 0.0) -> Optional[float]:
    if len(daily_returns) < 30:
        return None
    excess = daily_returns - risk_free_rate / 252
    std = float(excess.std())
    if std == 0:
        return None
    return float(excess.mean() / std * np.sqrt(252))


def sortino_ratio(daily_returns: pd.Series, risk_free_rate: float = 0.0) -> Optional[float]:
    if len(daily_returns) < 30:
        return None
    excess = daily_returns - risk_free_rate / 252
    downside = excess[excess < 0]
    if len(downside) == 0:
        return None
    downside_std = float(downside.std())
    if downside_std == 0:
        return None
    return float(excess.mean() / downside_std * np.sqrt(252))


def var_historical(daily_returns: pd.Series, confidence: float = 0.95) -> Optional[float]:
    if len(daily_returns) < 30:
        return None
    return float(np.percentile(daily_returns, (1 - confidence) * 100))


def max_drawdown(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    rolling_max = equity_curve.cummax()
    drawdowns = (equity_curve - rolling_max) / rolling_max
    return float(drawdowns.min())


def cagr(equity_curve: pd.Series, trading_days: int = 252) -> Optional[float]:
    if len(equity_curve) < 2 or equity_curve.iloc[0] == 0:
        return None
    total_return = float(equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    years = len(equity_curve) / trading_days
    if years <= 0:
        return None
    return (1 + total_return) ** (1 / years) - 1


def beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> Optional[float]:
    if len(portfolio_returns) < 30 or len(benchmark_returns) < 30:
        return None
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 30:
        return None
    cov_matrix = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
    bench_var = cov_matrix[1, 1]
    if bench_var == 0:
        return None
    return float(cov_matrix[0, 1] / bench_var)


def calmar_ratio(equity_curve: pd.Series) -> Optional[float]:
    c = cagr(equity_curve)
    dd = max_drawdown(equity_curve)
    if c is None or dd == 0:
        return None
    return float(c / abs(dd))


def compute_all_metrics(
    equity_curve: pd.Series,
    benchmark_curve: Optional[pd.Series] = None,
) -> dict:
    if equity_curve.empty or len(equity_curve) < 2:
        return {
            "sharpe_ratio": None,
            "sortino_ratio": None,
            "var_95": None,
            "max_drawdown_pct": None,
            "beta": None,
            "calmar_ratio": None,
            "cagr": None,
            "total_return_pct": None,
            "days_computed": 0,
        }

    daily_returns = equity_curve.pct_change().dropna()

    bench_returns = None
    if benchmark_curve is not None and len(benchmark_curve) >= 2:
        bench_returns = benchmark_curve.pct_change().dropna()

    total_ret = None
    if equity_curve.iloc[0] != 0:
        total_ret = float((equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1) * 100

    return {
        "sharpe_ratio": sharpe_ratio(daily_returns),
        "sortino_ratio": sortino_ratio(daily_returns),
        "var_95": var_historical(daily_returns),
        "max_drawdown_pct": max_drawdown(equity_curve) * 100,
        "beta": beta(daily_returns, bench_returns) if bench_returns is not None else None,
        "calmar_ratio": calmar_ratio(equity_curve),
        "cagr": cagr(equity_curve),
        "total_return_pct": total_ret,
        "days_computed": len(equity_curve),
    }
