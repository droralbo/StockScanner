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
        if prev < upper <= last:
            signal = "SELL"
            reason = f"RSI חצה {upper:.0f} כלפי מעלה ({prev:.1f}→{last:.1f}) — Overbought"
        elif prev > lower >= last:
            signal = "BUY"
            reason = f"RSI חצה {lower:.0f} כלפי מטה ({prev:.1f}→{last:.1f}) — Oversold"

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
        k_last, k_prev = float(stoch[k_col].iloc[-1]), float(stoch[k_col].iloc[-2])
        d_last, d_prev = float(stoch[d_col].iloc[-1]), float(stoch[d_col].iloc[-2])

        signal: str | None = None
        reason = f"%K={k_last:.1f} %D={d_last:.1f}"
        if k_prev < d_prev and k_last > d_last and k_last < lower + 10:
            signal = "BUY"
            reason = f"Stoch bullish cross באזור oversold (%K={k_last:.1f})"
        elif k_prev > d_prev and k_last < d_last and k_last > upper - 10:
            signal = "SELL"
            reason = f"Stoch bearish cross באזור overbought (%K={k_last:.1f})"

        return IndicatorResult(
            name=self.name,
            value={"k": k_last, "d": d_last},
            signal=signal,
            strength=abs(k_last - 50) / 50,
            reason=reason,
            meta={"k_period": k_period, "d_period": d_period},
        )
