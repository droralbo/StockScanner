from datetime import datetime, timezone

from src.graph.state import SignalState
from src.storage.db import SignalStore
from src.utils.logging import get_logger
from src.web.broadcaster import SignalBroadcaster

log = get_logger(__name__)


def make_publish_node(store: SignalStore, broadcaster: SignalBroadcaster):
    async def publish(state: SignalState) -> dict:
        agg = state.get("aggregated")
        if not agg or state.get("suppressed"):
            return {"published_id": None}

        symbol = state["symbol"]
        signal_payload = {
            "symbol": symbol,
            "action": agg["action"],
            "score": agg["score"],
            "interval": state["interval"],
            "agreeing": agg["agreeing"],
            "total_active": agg["total_active"],
            "components": agg["components"],
            "narration": state.get("narration"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        signal_id = await store.save_signal(signal_payload)
        signal_payload["id"] = signal_id

        await broadcaster.publish(signal_payload)
        log.info("published signal #%d %s %s score=%.2f",
                 signal_id, symbol, agg["action"], agg["score"])
        return {"published_id": signal_id}

    return publish
