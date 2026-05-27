from src.graph.aggregator import aggregate
from src.graph.state import SignalState
from src.utils.logging import get_logger

log = get_logger(__name__)


async def aggregate_node(state: SignalState) -> dict:
    results = state.get("indicator_results", [])
    if not results:
        return {"aggregated": None}

    out = aggregate(results)
    if out:
        log.info(
            "aggregated %s: %s score=%.2f (%d/%d agree)",
            state.get("symbol"), out["action"], out["score"],
            out["agreeing"], out["total_active"],
        )
    return {"aggregated": out}
