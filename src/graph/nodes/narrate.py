from anthropic import AsyncAnthropic

from src.graph.state import SignalState
from src.utils.logging import get_logger

log = get_logger(__name__)


_SYSTEM = (
    "אתה אנליסט שווקים. תפקידך לנסח הסבר קצר ובהיר בעברית (2-3 משפטים) "
    "על Signal טכני שכבר חושב. אל תוסיף המלצות פעולה חדשות, אל תמציא נתונים. "
    "פשוט תאר במילים פשוטות מה האינדיקטורים מראים ומה זה אומר."
)


def make_narrate_node(client: AsyncAnthropic, model: str):
    async def narrate(state: SignalState) -> dict:
        agg = state.get("aggregated")
        if not agg or state.get("suppressed"):
            return {"narration": None}

        components_text = "\n".join(
            f"- {c['name']}: {c['signal']} (strength={c['strength']:.2f}) — {c['reason']}"
            for c in agg["components"]
        )

        user_msg = (
            f"Symbol: {state['symbol']}\n"
            f"Action: {agg['action']}\n"
            f"Score: {agg['score']}\n"
            f"Indicators ({agg['agreeing']}/{agg['total_active']} agree):\n"
            f"{components_text}\n\n"
            "נסח לי 2-3 משפטים בעברית שמסבירים את ה-Signal."
        )

        try:
            resp = await client.messages.create(
                model=model,
                max_tokens=300,
                system=_SYSTEM,
                messages=[{"role": "user", "content": user_msg}],
            )
            text = "".join(
                block.text for block in resp.content if hasattr(block, "text")
            ).strip()
            return {"narration": text}
        except Exception as e:
            log.error("narration failed: %s", e)
            return {"narration": None}

    return narrate
