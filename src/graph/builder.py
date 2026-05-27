from anthropic import AsyncAnthropic
from langgraph.graph import END, START, StateGraph

from src.data.provider import DataProvider
from src.graph.nodes.aggregate import aggregate_node
from src.graph.nodes.analyze import compute_one, dispatch_indicators, skip_analyze
from src.graph.nodes.dedup import make_dedup_node
from src.graph.nodes.fetch import make_fetch_node
from src.graph.nodes.narrate import make_narrate_node
from src.graph.nodes.publish import make_publish_node
from src.graph.state import SignalState
from src.storage.db import SignalStore
from src.web.broadcaster import SignalBroadcaster


def build_signal_graph(
    provider: DataProvider,
    store: SignalStore,
    broadcaster: SignalBroadcaster,
    anthropic_client: AsyncAnthropic,
    anthropic_model: str,
):
    """Construct the LangGraph for one symbol run.

    Flow:
        START → fetch
                  ├─→ skip_analyze → END        (if fetch failed)
                  └─→ compute_one (parallel)   (one Send per indicator)
                       ↓
                      aggregate → dedup
                                    ├─→ narrate → publish → END
                                    └─→ END                  (no signal / suppressed)
    """
    g = StateGraph(SignalState)

    g.add_node("fetch", make_fetch_node(provider))
    g.add_node("compute_one", compute_one)
    g.add_node("skip_analyze", skip_analyze)
    g.add_node("aggregate", aggregate_node)
    g.add_node("dedup", make_dedup_node(store))
    g.add_node("narrate", make_narrate_node(anthropic_client, anthropic_model))
    g.add_node("publish", make_publish_node(store, broadcaster))

    g.add_edge(START, "fetch")
    g.add_conditional_edges(
        "fetch",
        dispatch_indicators,
        ["compute_one", "skip_analyze"],
    )
    g.add_edge("compute_one", "aggregate")
    g.add_edge("skip_analyze", END)

    g.add_conditional_edges(
        "aggregate",
        _should_dedup,
        {"dedup": "dedup", "end": END},
    )
    g.add_conditional_edges(
        "dedup",
        _should_narrate,
        {"narrate": "narrate", "end": END},
    )
    g.add_edge("narrate", "publish")
    g.add_edge("publish", END)

    return g.compile()


def _should_dedup(state: SignalState) -> str:
    return "dedup" if state.get("aggregated") else "end"


def _should_narrate(state: SignalState) -> str:
    return "end" if state.get("suppressed") else "narrate"
