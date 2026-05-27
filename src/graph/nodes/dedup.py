from src.graph.state import SignalState
from src.storage.db import SignalStore
from src.utils.logging import get_logger

log = get_logger(__name__)


def make_dedup_node(store: SignalStore):
    async def dedup(state: SignalState) -> dict:
        agg = state.get("aggregated")
        if not agg:
            return {"suppressed": False}

        symbol = state["symbol"]
        action = agg["action"]
        cooldown = state.get("cooldown_minutes", 60)

        recent = await store.has_recent_signal(symbol, action, cooldown)
        if recent:
            log.info("suppressed duplicate %s %s (within %dmin)", symbol, action, cooldown)
            return {"suppressed": True}
        return {"suppressed": False}

    return dedup
