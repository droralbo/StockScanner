from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd


@dataclass
class IndicatorResult:
    name: str
    value: dict[str, float]
    signal: str | None = None       # "BUY" / "SELL" / None
    strength: float = 0.0           # 0..1
    reason: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Indicator(ABC):
    name: str = ""
    requires_columns: list[str] = ["close"]
    min_candles: int = 30

    def __init__(self, **params: Any):
        self.params = params

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> IndicatorResult: ...

    def _validate(self, df: pd.DataFrame) -> None:
        missing = [c for c in self.requires_columns if c not in df.columns]
        if missing:
            raise ValueError(f"{self.name} missing columns: {missing}")
        if len(df) < self.min_candles:
            raise ValueError(
                f"{self.name} needs ≥{self.min_candles} candles, got {len(df)}"
            )


# ---- Registry ----------------------------------------------------------------

_REGISTRY: dict[str, type[Indicator]] = {}


def register(cls: type[Indicator]) -> type[Indicator]:
    if not cls.name:
        raise ValueError(f"{cls.__name__} must set `name` class attribute")
    if cls.name in _REGISTRY:
        raise ValueError(f"indicator already registered: {cls.name}")
    _REGISTRY[cls.name] = cls
    return cls


def build(name: str, **params: Any) -> Indicator:
    if name not in _REGISTRY:
        raise KeyError(
            f"unknown indicator: {name!r}. Available: {sorted(_REGISTRY.keys())}"
        )
    return _REGISTRY[name](**params)


def available() -> list[str]:
    return sorted(_REGISTRY.keys())


def load_all_indicators() -> None:
    """Import all indicator modules so their @register decorators run."""
    from src.indicators import momentum, trend, volatility, volume  # noqa: F401
