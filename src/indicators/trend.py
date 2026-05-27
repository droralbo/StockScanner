import pandas as pd
import pandas_ta as ta

from src.indicators.base import Indicator, IndicatorResult, register


@register
class MACD(Indicator):
    name = "macd"
    requires_columns = ["close"]
    min_candles = 60

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        self._validate(df)
        fast = int(self.params.get("fast", 12))
        slow = int(self.params.get("slow", 26))
        signal_period = int(self.params.get("signal", 9))

        macd_df = ta.macd(df["close"], fast=fast, slow=slow, signal=signal_period)
        macd_col, sig_col, hist_col = macd_df.columns[0], macd_df.columns[2], macd_df.columns[1]

        macd_last = float(macd_df[macd_col].iloc[-1])
        macd_prev = float(macd_df[macd_col].iloc[-2])
        sig_last = float(macd_df[sig_col].iloc[-1])
        sig_prev = float(macd_df[sig_col].iloc[-2])
        hist_last = float(macd_df[hist_col].iloc[-1])

        signal: str | None = None
        reason = f"MACD={macd_last:.3f} signal={sig_last:.3f}"
        if macd_prev <= sig_prev and macd_last > sig_last:
            signal = "BUY"
            reason = f"MACD bullish cross — חצה מעל ה-signal line ({macd_last:.3f} > {sig_last:.3f})"
        elif macd_prev >= sig_prev and macd_last < sig_last:
            signal = "SELL"
            reason = f"MACD bearish cross — חצה מתחת ל-signal line ({macd_last:.3f} < {sig_last:.3f})"

        strength = min(abs(hist_last) / max(abs(macd_last), 1e-6), 1.0)

        return IndicatorResult(
            name=self.name,
            value={"macd": macd_last, "signal": sig_last, "hist": hist_last},
            signal=signal,
            strength=strength,
            reason=reason,
            meta={"fast": fast, "slow": slow, "signal_period": signal_period},
        )


@register
class EMACross(Indicator):
    name = "ema_cross"
    requires_columns = ["close"]
    min_candles = 60

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        self._validate(df)
        fast = int(self.params.get("fast", 9))
        slow = int(self.params.get("slow", 21))

        ema_fast = ta.ema(df["close"], length=fast)
        ema_slow = ta.ema(df["close"], length=slow)

        f_last, f_prev = float(ema_fast.iloc[-1]), float(ema_fast.iloc[-2])
        s_last, s_prev = float(ema_slow.iloc[-1]), float(ema_slow.iloc[-2])

        signal: str | None = None
        reason = f"EMA{fast}={f_last:.2f} EMA{slow}={s_last:.2f}"
        if f_prev <= s_prev and f_last > s_last:
            signal = "BUY"
            reason = f"Golden cross — EMA{fast} חצה מעל EMA{slow}"
        elif f_prev >= s_prev and f_last < s_last:
            signal = "SELL"
            reason = f"Death cross — EMA{fast} חצה מתחת EMA{slow}"

        spread = abs(f_last - s_last) / max(s_last, 1e-6)
        return IndicatorResult(
            name=self.name,
            value={f"ema_{fast}": f_last, f"ema_{slow}": s_last, "spread_pct": spread * 100},
            signal=signal,
            strength=min(spread * 50, 1.0),
            reason=reason,
            meta={"fast": fast, "slow": slow},
        )


@register
class ADX(Indicator):
    """ADX measures trend strength. Reports a signal only when trend forms/breaks."""

    name = "adx"
    requires_columns = ["high", "low", "close"]
    min_candles = 50

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        self._validate(df)
        period = int(self.params.get("period", 14))
        threshold = float(self.params.get("threshold", 25))

        adx_df = ta.adx(df["high"], df["low"], df["close"], length=period)
        adx_col = [c for c in adx_df.columns if c.startswith("ADX")][0]
        dmp_col = [c for c in adx_df.columns if c.startswith("DMP")][0]
        dmn_col = [c for c in adx_df.columns if c.startswith("DMN")][0]

        adx_last = float(adx_df[adx_col].iloc[-1])
        adx_prev = float(adx_df[adx_col].iloc[-2])
        dmp = float(adx_df[dmp_col].iloc[-1])
        dmn = float(adx_df[dmn_col].iloc[-1])

        signal: str | None = None
        reason = f"ADX={adx_last:.1f} (+DI={dmp:.1f}, -DI={dmn:.1f})"
        if adx_prev < threshold <= adx_last:
            direction = "BUY" if dmp > dmn else "SELL"
            signal = direction
            reason = f"ADX חצה {threshold:.0f} — מתפתח טרנד {direction} (ADX={adx_last:.1f})"

        return IndicatorResult(
            name=self.name,
            value={"adx": adx_last, "plus_di": dmp, "minus_di": dmn},
            signal=signal,
            strength=min(adx_last / 50, 1.0),
            reason=reason,
            meta={"period": period, "threshold": threshold},
        )
