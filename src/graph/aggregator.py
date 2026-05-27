"""Pure aggregation logic — easy to unit test, no LangGraph dependency."""
from __future__ import annotations

from src.indicators.base import IndicatorResult


def aggregate(
    results: list[IndicatorResult],
    *,
    min_agreement: int = 2,
    min_majority_ratio: float = 0.6,
) -> dict | None:
    """
    Decide if a coherent BUY/SELL signal emerges.

    Returns None if no clear consensus, else:
        {
            "action": "BUY" | "SELL",
            "score": float,                      # weighted by strength
            "agreeing": int,                     # how many indicators agree
            "total_active": int,                 # how many produced any signal
            "components": [ {name, signal, strength, reason}, ... ],
        }

    Rules:
      - at least `min_agreement` indicators must point the same direction
      - the agreeing side must hold ≥ `min_majority_ratio` of all active signals
      - score = avg(strength) of agreeing components
    """
    active = [r for r in results if r.signal in ("BUY", "SELL")]
    if not active or len(active) < min_agreement:
        return None

    buys = [r for r in active if r.signal == "BUY"]
    sells = [r for r in active if r.signal == "SELL"]

    if len(buys) >= len(sells):
        winner, action = buys, "BUY"
    else:
        winner, action = sells, "SELL"

    if len(winner) < min_agreement:
        return None
    if len(winner) / len(active) < min_majority_ratio:
        return None

    score = sum(r.strength for r in winner) / len(winner)

    components = [
        {
            "name": r.name,
            "signal": r.signal,
            "strength": r.strength,
            "reason": r.reason,
            "value": r.value,
        }
        for r in results
        if r.signal is not None
    ]

    return {
        "action": action,
        "score": round(score, 3),
        "agreeing": len(winner),
        "total_active": len(active),
        "total_indicators": len(results),
        "components": components,
    }
