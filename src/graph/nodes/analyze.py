"""Parallel analyze step using LangGraph's `Send` API.

`dispatch_indicators` is the routing function returning a list of `Send` objects,
one per indicator. Each Send invokes `compute_one` with that indicator's payload.
LangGraph fans them out and rejoins on the `indicator_results` channel
(declared as Annotated[list, operator.add] in SignalState).
"""
from __future__ import annotations

from typing import Any

from langgraph.types import Send

from src.graph.state import SignalState
from src.indicators.base import IndicatorResult, build
from src.utils.logging import get_logger

log = get_logger(__name__)


def dispatch_indicators(state: SignalState) -> list[Send] | str:
    if state.get("candles") is None or state.get("error"):
        return "skip_analyze"

    candles = state["candles"]
    return [
        Send(
            "compute_one",
            {
                "name": cfg["name"],
                "params": cfg.get("params", {}),
                "candles": candles,
            },
        )
        for cfg in state["indicator_configs"]
    ]


async def compute_one(payload: dict[str, Any]) -> dict:
    """Compute a single indicator. Errors become a no-signal result with reason."""
    name = payload["name"]
    params = payload.get("params", {})
    candles = payload["candles"]
    try:
        result = build(name, **params).compute(candles)
    except Exception as e:
        log.warning("indicator %s failed: %s", name, e)
        result = IndicatorResult(
            name=name, value={}, signal=None, strength=0.0,
            reason=f"error: {e}",
        )
    return {"indicator_results": [result]}


async def skip_analyze(state: SignalState) -> dict:
    """No-op when fetch failed — keeps graph flowing to END."""
    return {}
