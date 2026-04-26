"""
Backtest and metrics evaluation.
Usage: python ml/evaluate.py
"""
import glob
import json
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from config import get_settings
from ml.features import FEATURE_COLS, prepare_dataset, make_labels, engineer_features

INITIAL_CASH = 100_000.0
COMMISSION = 1.0
SLIPPAGE_PCT = 0.0005
CONFIDENCE_THRESHOLD = 0.65


def run_backtest(symbol: str, model, lookback_years: int = 5) -> dict:
    df = yf.download(symbol, period=f"{lookback_years}y", auto_adjust=True, progress=False)
    if df.empty:
        return {}

    df_feat = engineer_features(df)
    df_clean = df_feat.dropna(subset=FEATURE_COLS)
    if len(df_clean) < 50:
        return {}

    X = df_clean[FEATURE_COLS]
    proba = model.predict_proba(X)[:, 1]

    close = df["Close"].reindex(df_clean.index)

    cash = INITIAL_CASH
    position = 0.0
    avg_cost = 0.0
    trades: list[dict] = []
    equity_curve: list[float] = []

    for i in range(len(df_clean)):
        current_close = float(close.iloc[i])
        conf = proba[i]
        total_equity = cash + position * current_close
        equity_curve.append(total_equity)

        if conf >= CONFIDENCE_THRESHOLD and position == 0:
            fill = current_close * (1 + SLIPPAGE_PCT)
            shares = (cash - COMMISSION) / fill
            if shares > 0:
                cash -= shares * fill + COMMISSION
                avg_cost = fill
                position = shares
                trades.append({"date": df_clean.index[i], "side": "buy", "price": fill, "shares": shares})

        elif conf <= (1 - CONFIDENCE_THRESHOLD) and position > 0:
            fill = current_close * (1 - SLIPPAGE_PCT)
            pnl = (fill - avg_cost) * position - COMMISSION
            cash += position * fill - COMMISSION
            trades.append({"date": df_clean.index[i], "side": "sell", "price": fill, "shares": position, "pnl": pnl})
            position = 0
            avg_cost = 0

    if position > 0:
        final_price = float(close.iloc[-1])
        equity_curve[-1] = cash + position * final_price

    eq = pd.Series(equity_curve)
    daily_returns = eq.pct_change().dropna()

    def sharpe(returns):
        if len(returns) < 30 or returns.std() == 0:
            return None
        return float(returns.mean() / returns.std() * np.sqrt(252))

    def sortino(returns):
        down = returns[returns < 0]
        if len(down) == 0 or down.std() == 0:
            return None
        return float(returns.mean() / down.std() * np.sqrt(252))

    def max_dd(curve):
        roll_max = curve.cummax()
        return float(((curve - roll_max) / roll_max).min())

    years = len(eq) / 252
    total_ret = (eq.iloc[-1] / INITIAL_CASH) - 1 if INITIAL_CASH > 0 else 0
    cagr = (1 + total_ret) ** (1 / years) - 1 if years > 0 else 0

    sell_trades = [t for t in trades if t["side"] == "sell"]
    win_rate = sum(1 for t in sell_trades if t.get("pnl", 0) > 0) / len(sell_trades) if sell_trades else None
    dd = max_dd(eq)
    calmar = cagr / abs(dd) if dd != 0 else None

    return {
        "symbol": symbol,
        "trades": len(sell_trades),
        "win_rate": round(win_rate, 4) if win_rate else None,
        "sharpe": round(sharpe(daily_returns), 4) if sharpe(daily_returns) else None,
        "sortino": round(sortino(daily_returns), 4) if sortino(daily_returns) else None,
        "cagr": round(cagr, 4),
        "max_drawdown": round(dd, 4),
        "total_return_pct": round(total_ret * 100, 2),
        "calmar": round(calmar, 4) if calmar else None,
    }


def main() -> None:
    settings = get_settings()
    pattern = os.path.join(settings.model_dir, "xgb_*.pkl")
    files = sorted(glob.glob(pattern), reverse=True)
    if not files:
        print(f"[evaluate] No model found in {settings.model_dir}")
        sys.exit(1)

    model_path = files[0]
    print(f"[evaluate] Loading model: {model_path}")
    model = joblib.load(model_path)

    print(f"\n{'Symbol':<8} {'Trades':>6} {'WinRate':>8} {'Sharpe':>8} {'Sortino':>8} {'CAGR':>7} {'MaxDD':>8} {'Calmar':>8}")
    print("-" * 70)

    all_pass = True
    for symbol in settings.watchlist:
        result = run_backtest(symbol, model, settings.historical_backfill_years)
        if not result:
            print(f"{symbol:<8} {'N/A':>6}")
            continue

        sharpe_val = result.get("sharpe") or 0
        if sharpe_val < 0:
            all_pass = False

        print(
            f"{symbol:<8}"
            f" {result.get('trades', 0):>6}"
            f" {str(result.get('win_rate') or 'N/A'):>8}"
            f" {str(result.get('sharpe') or 'N/A'):>8}"
            f" {str(result.get('sortino') or 'N/A'):>8}"
            f" {str(result.get('cagr', 0)):>7}"
            f" {str(result.get('max_drawdown', 0)):>8}"
            f" {str(result.get('calmar') or 'N/A'):>8}"
        )

    if not all_pass:
        print("\n[evaluate] WARNING: Some symbols have negative Sharpe ratio")
        sys.exit(1)
    else:
        print("\n[evaluate] All symbols passed Sharpe > 0 sanity check")


if __name__ == "__main__":
    main()
