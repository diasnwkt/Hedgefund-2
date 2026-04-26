import numpy as np
import pandas as pd
import pytest

from strategies.ml_strategy import XGBoostStrategy, FEATURE_COLS


def make_feature_df(n: int = 100, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    data = {col: rng.normal(0, 1, n) for col in FEATURE_COLS}
    data["ma_cross"] = rng.choice([-1, 0, 1], n)
    return pd.DataFrame(data)


def make_labels(n: int = 100, seed: int = 42) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.choice([0, 1], n))


def test_train_and_generate_signal():
    strategy = XGBoostStrategy(random_seed=42)
    X = make_feature_df()
    y = make_labels()
    strategy.train(X, y)
    result = strategy.generate_signal(X, "AAPL")
    assert result.signal in {"BUY", "SELL", "HOLD"}
    assert 0.0 <= result.confidence <= 1.0


def test_confidence_threshold_respected():
    strategy = XGBoostStrategy(random_seed=42, confidence_threshold=0.65)
    X = make_feature_df()
    y = make_labels()
    strategy.train(X, y)
    result = strategy.generate_signal(X, "AAPL")
    if result.signal == "BUY":
        assert result.confidence >= 0.65
    elif result.signal == "SELL":
        assert result.confidence <= 0.35


def test_hold_when_no_features():
    strategy = XGBoostStrategy(random_seed=42)
    X = make_feature_df()
    y = make_labels()
    strategy.train(X, y)
    empty_df = pd.DataFrame(columns=FEATURE_COLS)
    result = strategy.generate_signal(empty_df, "AAPL")
    assert result.signal == "HOLD"
    assert result.confidence == 0.0


def test_untrained_raises():
    strategy = XGBoostStrategy(random_seed=42)
    X = make_feature_df()
    with pytest.raises(RuntimeError, match="not loaded"):
        strategy.generate_signal(X, "AAPL")


def test_save_and_load(tmp_path):
    strategy = XGBoostStrategy(random_seed=42)
    X = make_feature_df()
    y = make_labels()
    strategy.train(X, y)
    strategy.model_version = "xgb_test_v1"

    pkl_path = str(tmp_path / "model.pkl")
    strategy.save(pkl_path)

    loaded = XGBoostStrategy(random_seed=42)
    loaded.load(pkl_path)
    assert loaded.model_version == "xgb_test_v1"
    result = loaded.generate_signal(X, "AAPL")
    assert result.signal in {"BUY", "SELL", "HOLD"}
