"""Synthetic candle generators for indicator unit tests."""
from __future__ import annotations

import numpy as np
import pandas as pd


def synth_candles(
    closes: list[float] | np.ndarray,
    volume: float = 1_000_000,
    start: str = "2026-01-01",
) -> pd.DataFrame:
    """Build OHLCV from a list of closes — high/low ±0.5%, open = prev close."""
    closes = np.asarray(closes, dtype=float)
    idx = pd.date_range(start, periods=len(closes), freq="5min", tz="UTC")
    opens = np.r_[closes[0], closes[:-1]]
    highs = np.maximum(opens, closes) * 1.005
    lows = np.minimum(opens, closes) * 0.995
    volumes = np.full(len(closes), volume)
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=idx,
    )


def rsi_oversold_recovery(n: int = 60) -> pd.DataFrame:
    """Closes that drive RSI deep below 30 then bounce above — should trigger BUY on last bar."""
    down = np.linspace(100, 70, n - 2)
    bounce = [72.0, 74.0]
    return synth_candles(np.r_[down, bounce])


def rsi_overbought_breakdown(n: int = 60) -> pd.DataFrame:
    up = np.linspace(70, 100, n - 2)
    drop = [97.0, 94.0]
    return synth_candles(np.r_[up, drop])


def steady_uptrend(n: int = 80, start: float = 100.0) -> pd.DataFrame:
    closes = np.linspace(start, start * 1.20, n)
    closes = closes + np.sin(np.linspace(0, 8, n)) * 0.3
    return synth_candles(closes)
