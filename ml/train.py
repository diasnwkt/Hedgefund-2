"""
Offline ML training entrypoint.
Walk-forward cross-validation with expanding window, 252-day test folds.
Usage: python ml/train.py
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.metrics import accuracy_score, roc_auc_score
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from config import get_settings
from ml.features import FEATURE_COLS, prepare_dataset

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)


def walk_forward_cv(X: pd.DataFrame, y: pd.Series, test_size: int = 252, min_train: int = 504):
    results = []
    n = len(X)
    start = min_train

    while start + test_size <= n:
        X_train, y_train = X.iloc[:start], y.iloc[:start]
        X_test, y_test = X.iloc[start : start + test_size], y.iloc[start : start + test_size]

        model = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=RANDOM_SEED,
            eval_metric="logloss",
            use_label_encoder=False,
        )
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

        preds = model.predict(X_test)
        proba = model.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, preds)
        auc = roc_auc_score(y_test, proba) if len(np.unique(y_test)) > 1 else 0.5
        results.append({"fold_start": start, "accuracy": acc, "auc": auc, "test_size": len(X_test)})
        start += test_size

    return results


def main() -> None:
    settings = get_settings()
    print(f"[train] Starting walk-forward training")
    print(f"[train] Watchlist: {settings.watchlist}")
    print(f"[train] Model dir: {settings.model_dir}")

    all_X, all_y = [], []

    for symbol in settings.watchlist:
        print(f"[train] Downloading {symbol}...")
        df = yf.download(symbol, period=f"{settings.historical_backfill_years}y", auto_adjust=True, progress=False)
        if df.empty:
            print(f"[train] WARNING: no data for {symbol}")
            continue
        X, y = prepare_dataset(df)
        all_X.append(X)
        all_y.append(y)

    if not all_X:
        print("[train] ERROR: no data available for training")
        sys.exit(1)

    X_combined = pd.concat(all_X, ignore_index=True)
    y_combined = pd.concat(all_y, ignore_index=True)

    print(f"[train] Dataset size: {len(X_combined)} samples, {float(y_combined.mean()):.1%} positive")

    cv_results = walk_forward_cv(X_combined, y_combined, test_size=settings.walk_forward_test_days)
    if cv_results:
        avg_acc = np.mean([r["accuracy"] for r in cv_results])
        avg_auc = np.mean([r["auc"] for r in cv_results])
        print(f"[train] Walk-forward CV: accuracy={avg_acc:.4f}, AUC={avg_auc:.4f} ({len(cv_results)} folds)")
    else:
        avg_acc = avg_auc = 0.0
        print("[train] WARNING: insufficient data for walk-forward CV")

    # Final model on all data
    final_model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=RANDOM_SEED,
        eval_metric="logloss",
        use_label_encoder=False,
    )
    final_model.fit(X_combined, y_combined, verbose=False)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    run_id = datetime.now(timezone.utc).strftime("%H%M%S")
    model_version = f"xgb_{timestamp}_{run_id}"

    import joblib
    os.makedirs(settings.model_dir, exist_ok=True)
    pkl_path = os.path.join(settings.model_dir, f"{model_version}.pkl")
    meta_path = os.path.join(settings.model_dir, f"{model_version}.json")

    joblib.dump(final_model, pkl_path)
    meta = {
        "model_version": model_version,
        "feature_cols": FEATURE_COLS,
        "confidence_threshold": settings.signal_confidence_threshold,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "training_samples": len(X_combined),
        "positive_rate": float(y_combined.mean()),
        "cv_folds": len(cv_results),
        "cv_avg_accuracy": round(avg_acc, 4),
        "cv_avg_auc": round(avg_auc, 4),
        "random_seed": RANDOM_SEED,
        "symbols": settings.watchlist,
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[train] Model saved: {pkl_path}")
    print(f"[train] Metadata: {meta_path}")
    print(f"[train] Version: {model_version}")


if __name__ == "__main__":
    main()
