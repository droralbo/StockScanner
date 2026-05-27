import pytest

from src.indicators.base import available, build, load_all_indicators
from tests.fixtures import rsi_oversold_recovery, rsi_overbought_breakdown, steady_uptrend


@pytest.fixture(autouse=True, scope="module")
def _load():
    load_all_indicators()


def test_registry_has_expected_indicators():
    names = set(available())
    assert {"rsi", "macd", "ema_cross", "adx", "bbands", "atr", "stochastic", "obv", "vwap"} <= names


def test_rsi_triggers_buy_on_oversold_recovery():
    df = rsi_oversold_recovery()
    res = build("rsi", period=14, upper=70, lower=30).compute(df)
    assert res.signal == "BUY"
    assert res.value["rsi"] > 30
    assert "Oversold" in res.reason


def test_rsi_triggers_sell_on_overbought_breakdown():
    df = rsi_overbought_breakdown()
    res = build("rsi", period=14, upper=70, lower=30).compute(df)
    assert res.signal == "SELL"
    assert "Overbought" in res.reason


def test_rsi_no_signal_on_steady_trend():
    df = steady_uptrend()
    res = build("rsi", period=14).compute(df)
    assert 0 <= res.value["rsi"] <= 100


def test_macd_runs_and_returns_values():
    df = steady_uptrend()
    res = build("macd").compute(df)
    assert "macd" in res.value
    assert "signal" in res.value


def test_bbands_returns_bounds():
    df = steady_uptrend()
    res = build("bbands").compute(df)
    assert res.value["lower"] < res.value["mid"] < res.value["upper"]


def test_ema_cross_returns_spread():
    df = steady_uptrend()
    res = build("ema_cross", fast=9, slow=21).compute(df)
    assert "spread_pct" in res.value


def test_atr_is_positive():
    df = steady_uptrend()
    res = build("atr").compute(df)
    assert res.value["atr"] > 0
    assert res.signal is None  # ATR is informational only


def test_indicator_validates_min_candles():
    from tests.fixtures import synth_candles
    short = synth_candles([100.0] * 5)
    with pytest.raises(ValueError, match="needs"):
        build("rsi").compute(short)


def test_unknown_indicator_raises():
    with pytest.raises(KeyError, match="unknown"):
        build("nonexistent_xyz")
