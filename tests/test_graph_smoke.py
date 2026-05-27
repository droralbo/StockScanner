"""Smoke test — wire the graph with mocks and verify a BUY signal flows end-to-end."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from src.data.provider import DataProvider
from src.graph.builder import build_signal_graph
from src.graph.state import SignalState
from src.indicators.base import load_all_indicators
from src.storage.db import SignalStore
from src.web.broadcaster import SignalBroadcaster
from tests.fixtures import rsi_oversold_recovery


class _MockProvider(DataProvider):
    def __init__(self, df):
        self.df = df

    async def get_candles(self, symbol, interval, limit=200):
        return self.df

    async def close(self):
        pass


@pytest.fixture(scope="module", autouse=True)
def _load():
    load_all_indicators()


@pytest.fixture
async def store(tmp_path):
    s = SignalStore(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await s.init()
    yield s
    await s.close()


@pytest.fixture
def broadcaster():
    return SignalBroadcaster()


@pytest.fixture
def mock_anthropic():
    client = AsyncMock()
    msg = AsyncMock()
    msg.content = [type("Block", (), {"text": "RSI recovered from oversold."})()]
    client.messages.create = AsyncMock(return_value=msg)
    return client


async def test_buy_signal_flows_through_graph(store, broadcaster, mock_anthropic):
    df = rsi_oversold_recovery()
    provider = _MockProvider(df)

    graph = build_signal_graph(
        provider=provider,
        store=store,
        broadcaster=broadcaster,
        anthropic_client=mock_anthropic,
        anthropic_model="claude-haiku-4-5-20251001",
    )

    state: SignalState = {
        "symbol": "TEST",
        "interval": "5",
        "candles_limit": 200,
        "cooldown_minutes": 60,
        "indicator_configs": [
            {"name": "rsi", "params": {"period": 14, "upper": 70, "lower": 30}},
            {"name": "macd", "params": {}},
            {"name": "ema_cross", "params": {"fast": 9, "slow": 21}},
        ],
        "indicator_results": [],
        "suppressed": False,
    }

    final = await graph.ainvoke(state)

    assert final.get("aggregated") is not None
    assert final["aggregated"]["action"] == "BUY"
    assert final.get("published_id") is not None

    # signal landed in DB
    recent = await store.recent_signals(limit=10)
    assert len(recent) == 1
    assert recent[0]["symbol"] == "TEST"
    assert recent[0]["action"] == "BUY"


async def test_dedup_suppresses_second_identical_signal(store, broadcaster, mock_anthropic):
    df = rsi_oversold_recovery()
    provider = _MockProvider(df)
    graph = build_signal_graph(
        provider=provider,
        store=store,
        broadcaster=broadcaster,
        anthropic_client=mock_anthropic,
        anthropic_model="claude-haiku-4-5-20251001",
    )

    base_state: SignalState = {
        "symbol": "DUPE",
        "interval": "5",
        "candles_limit": 200,
        "cooldown_minutes": 60,
        "indicator_configs": [
            {"name": "rsi", "params": {}},
            {"name": "macd", "params": {}},
            {"name": "ema_cross", "params": {}},
        ],
        "indicator_results": [],
        "suppressed": False,
    }

    first = await graph.ainvoke({**base_state, "indicator_results": []})
    second = await graph.ainvoke({**base_state, "indicator_results": []})

    assert first.get("published_id") is not None
    assert second.get("suppressed") is True
    assert second.get("published_id") is None
