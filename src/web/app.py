"""FastAPI app factory — wires everything together, plus lifespan that starts the scheduler."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from anthropic import AsyncAnthropic
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.data.marketdata_app import MarketDataAppProvider
from src.graph.builder import build_signal_graph
from src.indicators.base import load_all_indicators
from src.scheduler.runner import Scheduler
from src.storage.db import SignalStore
from src.utils.config import load_watchlist
from src.utils.logging import get_logger, setup_logging
from src.utils.settings import get_settings
from src.web import api, ws
from src.web.broadcaster import SignalBroadcaster

log = get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)
    load_all_indicators()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("starting up — model=%s", settings.anthropic_model)

        watchlist = load_watchlist(settings.watchlist_path)
        broadcaster = SignalBroadcaster()
        store = SignalStore(settings.database_url)
        await store.init()

        provider = MarketDataAppProvider(
            token=settings.marketdata_token,
            base_url=settings.marketdata_base_url,
            rate_limit_per_minute=settings.marketdata_rate_limit_per_minute,
        )
        anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        graph = build_signal_graph(
            provider=provider,
            store=store,
            broadcaster=broadcaster,
            anthropic_client=anthropic_client,
            anthropic_model=settings.anthropic_model,
        )

        scheduler = Scheduler(
            graph=graph,
            watchlist=watchlist,
            interval_seconds=settings.scheduler_interval_seconds,
            max_concurrency=settings.scheduler_max_concurrency,
        )

        app.state.watchlist = watchlist
        app.state.broadcaster = broadcaster
        app.state.store = store
        app.state.provider = provider
        app.state.scheduler = scheduler

        await scheduler.start()
        try:
            yield
        finally:
            log.info("shutting down")
            await scheduler.stop()
            await provider.close()
            await store.close()

    app = FastAPI(
        title="Stock Signals Agent",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(api.router, prefix="/api")
    app.include_router(ws.router)

    static_dir = Path(__file__).parent / "static"

    @app.get("/", include_in_schema=False)
    async def root():
        return FileResponse(static_dir / "index.html")

    app.mount("/", StaticFiles(directory=static_dir), name="static")

    return app
