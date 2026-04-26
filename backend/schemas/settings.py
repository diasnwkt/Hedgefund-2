from typing import Literal

from pydantic import BaseModel, field_validator


class WatchlistOut(BaseModel):
    symbols: list[str]
    count: int


class WatchlistUpdate(BaseModel):
    symbols: list[str]

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip().upper() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("symbols list cannot be empty")
        return cleaned


class ModeOut(BaseModel):
    mode: Literal["paper", "live"]
    live_enabled: bool


class ModeUpdate(BaseModel):
    mode: Literal["paper", "live"]
    confirm: str

    @field_validator("confirm")
    @classmethod
    def require_confirmation(cls, v: str, info) -> str:
        values = info.data
        if values.get("mode") == "live" and v != "I_UNDERSTAND_RISK":
            raise ValueError('To enable live mode, confirm must be "I_UNDERSTAND_RISK"')
        return v
