from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class OrderResult:
    external_id: Optional[str]
    symbol: str
    side: str
    shares: Decimal
    filled_price: Optional[Decimal]
    slippage: Decimal
    commission: Decimal
    status: str
    reason: Optional[str] = None


class BaseBroker(ABC):
    @abstractmethod
    async def submit_buy(
        self,
        symbol: str,
        shares: Decimal,
        current_price: Decimal,
        signal_id: Optional[int] = None,
    ) -> OrderResult:
        ...

    @abstractmethod
    async def submit_sell(
        self,
        symbol: str,
        shares: Decimal,
        current_price: Decimal,
        signal_id: Optional[int] = None,
    ) -> OrderResult:
        ...

    @abstractmethod
    async def get_current_price(self, symbol: str) -> Decimal:
        ...

    @abstractmethod
    async def get_account_cash(self) -> Decimal:
        ...
