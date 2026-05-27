from src.data.provider import DataProvider
from src.graph.state import SignalState
from src.utils.logging import get_logger

log = get_logger(__name__)


def make_fetch_node(provider: DataProvider):
    async def fetch(state: SignalState) -> dict:
        symbol = state["symbol"]
        interval = state["interval"]
        limit = state.get("candles_limit", 200)
        try:
            df = await provider.get_candles(symbol, interval, limit=limit)
            log.info("fetched %d candles for %s @ %s", len(df), symbol, interval)
            return {"candles": df}
        except Exception as e:
            log.error("fetch failed for %s: %s", symbol, e)
            return {"candles": None, "error": f"fetch: {e}"}

    return fetch
