from src.graph.aggregator import aggregate
from src.indicators.base import IndicatorResult


def _r(name, signal, strength=0.5):
    return IndicatorResult(name=name, value={}, signal=signal, strength=strength, reason="")


def test_no_signal_when_no_active():
    assert aggregate([_r("rsi", None), _r("macd", None)]) is None


def test_no_signal_below_min_agreement():
    assert aggregate([_r("rsi", "BUY")]) is None


def test_clean_buy_consensus():
    out = aggregate([_r("rsi", "BUY", 0.6), _r("macd", "BUY", 0.8), _r("ema_cross", "BUY", 0.4)])
    assert out["action"] == "BUY"
    assert out["agreeing"] == 3
    assert out["score"] == round((0.6 + 0.8 + 0.4) / 3, 3)


def test_no_signal_on_mixed_signals():
    out = aggregate([_r("rsi", "BUY"), _r("macd", "SELL"), _r("ema", "BUY"), _r("adx", "SELL")])
    assert out is None  # 2v2 — neither side reaches majority


def test_majority_threshold():
    out = aggregate(
        [_r("rsi", "BUY"), _r("macd", "BUY"), _r("ema", "SELL")],
        min_majority_ratio=0.6,
    )
    assert out["action"] == "BUY"
    assert out["agreeing"] == 2
