import pandas as pd
import pandas_ta as ta

from src.indicators.base import Indicator, IndicatorResult, register


@register
class BBands(Indicator):
    name = "bbands"
    requires_columns = ["close"]
    min_candles = 40

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        self._validate(df)
        period = int(self.params.get("period", 20))
        std = float(self.params.get("std", 2.0))

        bb = ta.bbands(df["close"], length=period, std=std)
        lower_col = [c for c in bb.columns if c.startswith("BBL")][0]
        mid_col = [c for c in bb.columns if c.startswith("BBM")][0]
        upper_col = [c for c in bb.columns if c.startswith("BBU")][0]

        lower = float(bb[lower_col].iloc[-1])
        mid = float(bb[mid_col].iloc[-1])
        upper = float(bb[upper_col].iloc[-1])
        close_last = float(df["close"].iloc[-1])
        close_prev = float(df["close"].iloc[-2])

        signal: str | None = None
        reason = f"close={close_last:.2f} BB[{lower:.2f}..{upper:.2f}]"

        if close_prev < lower and close_last >= lower:
            signal = "BUY"
            reason = f"Bollinger lower band bounce — close חזר מ-{close_prev:.2f} ל-{close_last:.2f}"
        elif close_prev > upper and close_last <= upper:
            signal = "SELL"
            reason = f"Bollinger upper band rejection — close ירד מ-{close_prev:.2f} ל-{close_last:.2f}"

        band_width = (upper - lower) / max(mid, 1e-6)
        position = (close_last - lower) / max(upper - lower, 1e-6)

        return IndicatorResult(
            name=self.name,
            value={
                "lower": lower, "mid": mid, "upper": upper,
                "close": close_last, "width_pct": band_width * 100,
                "position": position,
            },
            signal=signal,
            strength=min(band_width * 5, 1.0),
            reason=reason,
            meta={"period": period, "std": std},
        )


@register
class ATR(Indicator):
    """ATR is informational (volatility magnitude). No standalone signal."""

    name = "atr"
    requires_columns = ["high", "low", "close"]
    min_candles = 30

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        self._validate(df)
        period = int(self.params.get("period", 14))

        atr = ta.atr(df["high"], df["low"], df["close"], length=period)
        atr_last = float(atr.iloc[-1])
        close_last = float(df["close"].iloc[-1])
        atr_pct = atr_last / max(close_last, 1e-6) * 100

        return IndicatorResult(
            name=self.name,
            value={"atr": atr_last, "atr_pct": atr_pct},
            signal=None,
            strength=0.0,
            reason=f"ATR={atr_last:.2f} ({atr_pct:.2f}% מ-close)",
            meta={"period": period},
        )
