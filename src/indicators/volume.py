import pandas as pd
import pandas_ta as ta

from src.indicators.base import Indicator, IndicatorResult, register


@register
class OBV(Indicator):
    """On-Balance Volume. Signal on OBV slope reversal vs price."""

    name = "obv"
    requires_columns = ["close", "volume"]
    min_candles = 30

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        self._validate(df)
        lookback = int(self.params.get("lookback", 10))

        obv = ta.obv(df["close"], df["volume"])
        last = float(obv.iloc[-1])
        ref = float(obv.iloc[-lookback])

        price_last = float(df["close"].iloc[-1])
        price_ref = float(df["close"].iloc[-lookback])

        obv_trend = "up" if last > ref else "down"
        price_trend = "up" if price_last > price_ref else "down"

        signal: str | None = None
        reason = f"OBV trend={obv_trend}, price trend={price_trend}"

        # Divergence: price down + OBV up → bullish; price up + OBV down → bearish
        if price_trend == "down" and obv_trend == "up":
            signal = "BUY"
            reason = "Bullish OBV divergence — מחיר יורד אבל volume מצביע על צבירה"
        elif price_trend == "up" and obv_trend == "down":
            signal = "SELL"
            reason = "Bearish OBV divergence — מחיר עולה אבל volume חלש"

        change_pct = abs(last - ref) / max(abs(ref), 1e-6) * 100
        return IndicatorResult(
            name=self.name,
            value={"obv": last, "obv_ref": ref, "change_pct": change_pct},
            signal=signal,
            strength=min(change_pct / 20, 1.0),
            reason=reason,
            meta={"lookback": lookback},
        )


@register
class VWAP(Indicator):
    """VWAP — institutional reference. Signal: price crossing VWAP."""

    name = "vwap"
    requires_columns = ["high", "low", "close", "volume"]
    min_candles = 20

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        self._validate(df)

        vwap = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
        vwap_last = float(vwap.iloc[-1])
        close_last = float(df["close"].iloc[-1])
        close_prev = float(df["close"].iloc[-2])
        vwap_prev = float(vwap.iloc[-2])

        signal: str | None = None
        reason = f"close={close_last:.2f} vs VWAP={vwap_last:.2f}"

        if close_prev <= vwap_prev and close_last > vwap_last:
            signal = "BUY"
            reason = f"Price חצה VWAP כלפי מעלה ({close_last:.2f} > {vwap_last:.2f})"
        elif close_prev >= vwap_prev and close_last < vwap_last:
            signal = "SELL"
            reason = f"Price חצה VWAP כלפי מטה ({close_last:.2f} < {vwap_last:.2f})"

        deviation_pct = (close_last - vwap_last) / max(vwap_last, 1e-6) * 100
        return IndicatorResult(
            name=self.name,
            value={"vwap": vwap_last, "close": close_last, "deviation_pct": deviation_pct},
            signal=signal,
            strength=min(abs(deviation_pct) / 2, 1.0),
            reason=reason,
            meta={},
        )
