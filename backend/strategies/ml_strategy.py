import json
import os
from datetime import datetime, timezone
from typing import Optional

import joblib
import numpy as np
import pandas as pd
import structlog
from xgboost import XGBClassifier

from strategies.base import BaseStrategy, SignalResult

log = structlog.get_logger(__name__)

FEATURE_COLS = [
    "rsi_14", "macd", "macd_signal", "volume_zscore",
    "ma_20", "ma_50", "ma_cross", "momentum_5d", "momentum_20d",
]

TARGET_RETURN_THRESHOLD = 0.01  # 1% forward return = positive label
FORWARD_DAYS = 5


class XGBoostStrategy(BaseStrategy):
    def __init__(self, random_seed: int = 42, n_jobs: int = -1, confidence_threshold: float = 0.65) -> None:
        self.random_seed = random_seed
        self.n_jobs = n_jobs
        self.confidence_threshold = confidence_threshold
        self.model: Optional[XGBClassifier] = None
        self.model_version: str = "untrained"
        self._feature_cols = FEATURE_COLS

    def _make_model(self) -> XGBClassifier:
        return XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=self.random_seed,
            n_jobs=self.n_jobs,
            eval_metric="logloss",
            use_label_encoder=False,
        )

    def train(self, features: pd.DataFrame, labels: pd.Series) -> None:
        X = features[self._feature_cols].dropna()
        y = labels.loc[X.index]
        self.model = self._make_model()
        self.model.fit(X, y)
        log.info("xgboost_trained", samples=len(X), positive_rate=float(y.mean()))

    def generate_signal(self, features: pd.DataFrame, ticker: str) -> SignalResult:
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load() or train() first.")

        latest = features[self._feature_cols].dropna().tail(1)
        if latest.empty:
            return SignalResult(ticker=ticker, signal="HOLD", confidence=0.0, model_version=self.model_version)

        proba = self.model.predict_proba(latest)[0]
        confidence = float(proba[1])

        if confidence >= self.confidence_threshold:
            signal = "BUY"
        elif confidence <= (1.0 - self.confidence_threshold):
            signal = "SELL"
        else:
            signal = "HOLD"

        return SignalResult(
            ticker=ticker,
            signal=signal,
            confidence=confidence,
            model_version=self.model_version,
        )

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump(self.model, path)
        meta_path = path.replace(".pkl", ".json")
        meta = {
            "model_version": self.model_version,
            "feature_cols": self._feature_cols,
            "confidence_threshold": self.confidence_threshold,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
        log.info("model_saved", path=path)

    def load(self, path: str) -> None:
        self.model = joblib.load(path)
        meta_path = path.replace(".pkl", ".json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            self.model_version = meta.get("model_version", "unknown")
            self._feature_cols = meta.get("feature_cols", FEATURE_COLS)
        log.info("model_loaded", path=path, version=self.model_version)
