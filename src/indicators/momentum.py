import pandas as pd
import pandas_ta as ta

from src.indicators.base import Indicator, IndicatorResult, register


@register
class RSI(Indicator):
    name = "rsi"
    requires_columns = ["close"]
    min_candles = 30

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        self._validate(df)
        period = int(self.params.get("period", 14))
        upper = float(self.params.get("upper", 70))
        lower = float(self.params.get("lower", 30))

        rsi = ta.rsi(df["close"], length=period)
        last = float(rsi.iloc[-1])
        prev = float(rsi.iloc[-2])

        signal: str | None = None
        reason = f"RSI={last:.1f}"
        if prev <= lower < last:
            signal = "BUY"
            reason = f"RSI יצא מ-Oversold ({prev:.1f}→{last:.1f}) — Recovery"
        elif prev >= upper > last:
            signal = "SELL"
            reason = f"RSI נשבר מ-Overbought ({prev:.1f}→{last:.1f}) — Breakdown"

        return IndicatorResult(
            name=self.name,
            value={"rsi": last, "prev": prev},
            signal=signal,
            strength=min(abs(last - 50) / 50, 1.0),
            reason=reason,
            meta={"period": period, "upper": upper, "lower": lower},
        )


@register
class Stochastic(Indicator):
    name = "stochastic"
    requires_columns = ["high", "low", "close"]
    min_candles = 40

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        self._validate(df)
        k_period = int(self.params.get("k", 14))
        d_period = int(self.params.get("d", 3))
        upper = float(self.params.get("upper", 80))
        lower = float(self.params.get("lower", 20))

        stoch = ta.stoch(df["high"], df["low"], df["close"], k=k_period, d=d_period)
        k_col, d_col = stoch.columns[0], stoch.columns[1]
        k_last, d_last = float(stoch[k_col].iloc[-1]), float(stoch[d_col].iloc[-1])

        # Detect cross within the last 3 bars (hysteresis — realistic for slow signals)
        k_recent = stoch[k_col].iloc[-4:].values
        d_recent = stoch[d_col].iloc[-4:].values
        bull_cross = any(
            k_recent[i] < d_recent[i] and k_recent[i + 1] > d_recent[i + 1]
            for i in range(len(k_recent) - 1)
        ) and k_last > d_last
        bear_cross = any(
            k_recent[i] > d_recent[i] and k_recent[i + 1] < d_recent[i + 1]
            for i in range(len(k_recent) - 1)
        ) and k_last < d_last

        signal: str | None = None
        reason = f"%K={k_last:.1f} %D={d_last:.1f}"
        if bull_cross and k_last < lower + 30:
            signal = "BUY"
            reason = f"Stoch bullish cross יוצא מ-Oversold (%K={k_last:.1f})"
        elif bear_cross and k_last > upper - 30:
            signal = "SELL"
            reason = f"Stoch bearish cross יוצא מ-Overbought (%K={k_last:.1f})"

        return IndicatorResult(
            name=self.name,
            value={"k": k_last, "d": d_last},
            signal=signal,
            strength=abs(k_last - 50) / 50,
            reason=reason,
            meta={"k_period": k_period, "d_period": d_period},
        )
