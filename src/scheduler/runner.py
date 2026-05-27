"""Async scheduler — fires SignalGraph runs per symbol on a fixed interval."""
from __future__ import annotations

import asyncio
from datetime import datetime

from src.graph.state import SignalState
from src.utils.config import WatchlistConfig
from src.utils.logging import get_logger

log = get_logger(__name__)


class Scheduler:
    def __init__(
        self,
        graph,
        watchlist: WatchlistConfig,
        interval_seconds: int = 60,
        max_concurrency: int = 5,
    ):
        self.graph = graph
        self.watchlist = watchlist
        self.interval = interval_seconds
        self._sem = asyncio.Semaphore(max_concurrency)
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run_forever(), name="scheduler")
        log.info(
            "scheduler started — %d symbols, %ds interval, max_concurrency=%d",
            len(self.watchlist.symbols), self.interval, self._sem._value,
        )

    async def stop(self) -> None:
        self._stopping.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        log.info("scheduler stopped")

    async def _run_forever(self) -> None:
        while not self._stopping.is_set():
            tick_start = datetime.now()
            await self._tick()
            elapsed = (datetime.now() - tick_start).total_seconds()
            sleep_for = max(1, self.interval - elapsed)
            log.debug("tick done in %.2fs, sleeping %.2fs", elapsed, sleep_for)
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=sleep_for)
            except asyncio.TimeoutError:
                pass  # next tick

    async def _tick(self) -> None:
        tasks = [self._run_symbol(s) for s in self.watchlist.symbols]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_symbol(self, symbol_cfg) -> None:
        async with self._sem:
            state: SignalState = {
                "symbol": symbol_cfg.symbol,
                "interval": self.watchlist.get_interval(symbol_cfg),
                "candles_limit": self.watchlist.default_candles_limit,
                "cooldown_minutes": self.watchlist.get_cooldown(symbol_cfg),
                "indicator_configs": [
                    {"name": ind.name, "params": ind.params}
                    for ind in symbol_cfg.indicators
                ],
                "indicator_results": [],
                "suppressed": False,
            }
            try:
                await self.graph.ainvoke(state)
            except Exception as e:
                log.exception("graph run failed for %s: %s", symbol_cfg.symbol, e)
