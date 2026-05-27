from fastapi import APIRouter, Depends, Request

from src.storage.db import SignalStore
from src.utils.config import WatchlistConfig


router = APIRouter()


def get_store(request: Request) -> SignalStore:
    return request.app.state.store


def get_watchlist(request: Request) -> WatchlistConfig:
    return request.app.state.watchlist


@router.get("/health")
async def health(request: Request) -> dict:
    return {
        "status": "ok",
        "subscribers": request.app.state.broadcaster.subscriber_count,
    }


@router.get("/signals")
async def list_signals(
    symbol: str | None = None,
    limit: int = 50,
    store: SignalStore = Depends(get_store),
) -> list[dict]:
    limit = max(1, min(limit, 500))
    return await store.recent_signals(limit=limit, symbol=symbol)


@router.get("/symbols")
async def list_symbols(watchlist: WatchlistConfig = Depends(get_watchlist)) -> list[dict]:
    return [
        {
            "symbol": s.symbol,
            "interval": watchlist.get_interval(s),
            "indicators": [{"name": ind.name, "params": ind.params} for ind in s.indicators],
        }
        for s in watchlist.symbols
    ]
