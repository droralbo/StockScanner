from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

import pandas as pd

from src.indicators.base import IndicatorResult


class IndicatorJob(TypedDict):
    """Payload sent to each parallel analyze branch."""
    name: str
    params: dict[str, Any]
    candles: pd.DataFrame


class SignalState(TypedDict, total=False):
    symbol: str
    interval: str
    candles_limit: int
    cooldown_minutes: int
    indicator_configs: list[dict[str, Any]]   # [{name, params}, ...]

    candles: pd.DataFrame | None
    indicator_results: Annotated[list[IndicatorResult], operator.add]

    aggregated: dict[str, Any] | None         # {action, score, components, ...}
    suppressed: bool
    narration: str | None
    published_id: int | None
    error: str | None
