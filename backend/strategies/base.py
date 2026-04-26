from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass
class SignalResult:
    ticker: str
    signal: Literal["BUY", "SELL", "HOLD"]
    confidence: float
    model_version: str
    rationale: str = ""


class BaseStrategy(ABC):
    @abstractmethod
    def generate_signal(self, features: pd.DataFrame, ticker: str) -> SignalResult:
        """Generate a trading signal from a feature DataFrame."""

    @abstractmethod
    def train(self, features: pd.DataFrame, labels: pd.Series) -> None:
        """Train the strategy on historical features and labels."""

    @abstractmethod
    def load(self, path: str) -> None:
        """Load a saved model artifact."""

    @abstractmethod
    def save(self, path: str) -> None:
        """Save model artifact to path."""
