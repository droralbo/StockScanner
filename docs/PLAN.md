# Stock Signals Agentic System — תוכנית עבודה

## Context

המטרה: לבנות מערכת **Agentic** אוטונומית בפייתון שעוקבת אחר רשימת מניות, מנתחת אותן באמצעות אינדיקטורים טכניים מובילים (RSI, MACD, BBANDS, EMA cross, ADX, ATR, Stochastic, OBV, VWAP), ומציגה התראות "Signals" באפליקציית ווב חיה בזמן אמת.

**החלטות מפתח שנקבעו עם המשתמש:**
- **Framework:** LangGraph (state machine + multi-agent orchestration)
- **Data Source:** [marketdata.app](https://www.marketdata.app/) REST API — real-time stocks (Starter $12/חודש annual)
- **Channel:** **Web Application** (FastAPI + WebSocket) — דשבורד חי עם push real-time
- **Hosting:** **Railway** — single-process deployment (FastAPI server + scheduler background task)
- **תדירות:** Polling קבוע (1m/5m) + Signal event-driven (push ל-clients רק על טריגר)
- **Decision Logic:** Rule-based דטרמיניסטי (טריגרים מדויקים) + LLM (Claude) לניסוח ההודעה הסופית בלבד
- **קונפיגורציה:** YAML
- **דרישה מיוחדת:** Plugin-style indicator registry — להוסיף/להוריד אינדיקטור מקובץ YAML בלי לגעת בקוד

**Quota & אילוצים — marketdata.app:**
- **Free**: 100 credits/יום, 24h delayed → לא מתאים.
- **Starter** ($12/חודש annual, $30 חודשי): 10,000 credits/יום, **real-time stocks**. מאפשר ~25 מניות עם polling של דקה (390 calls/symbol/day × 25 ≈ 9,750).
- **Trader** ($30/חודש annual): 100K/יום, real-time גם options.
- REST בלבד (אין WebSocket). אין SDK פייתוני רשמי → נכתוב client דק עם `aiohttp`.
- אין אינדיקטורים מובנים → מחושבים מקומית עם `pandas-ta`.
- הקוד data-source-agnostic דרך `DataProvider` ABC — החלפה ל-Alpaca/Polygon/Finnhub בעתיד = class חדש בלבד.

**אילוצי Railway:**
- מחיר: $5/חודש Hobby plan (אחרי credits חינמיים).
- ה-app חייב להאזין על `$PORT`.
- Filesystem **ephemeral** ב-restart → SQLite חייב להיות על Railway Volume מותקן, או להחליף ל-Postgres (Railway מספק חינמי).
- אין long-lived process מובטח (Railway יכול לבצע restart) → כל ה-state חייב להישמר ב-DB ולא בזיכרון.

---

## Architecture — High-Level

```
                ┌──────────────────────────────────────────────┐
                │              Railway Container                │
                │                                                │
                │   ┌──────────────────────────────────────┐    │
                │   │           FastAPI Process            │    │
                │   │                                       │    │
                │   │   ┌─────────────────────────────┐    │    │
                │   │   │  Scheduler (asyncio task)   │    │    │
                │   │   │  tick every 60s per symbol  │    │    │
                │   │   └────────────┬────────────────┘    │    │
                │   │                ▼                      │    │
                │   │   ┌─────────────────────────────┐    │    │
                │   │   │   LangGraph: SignalGraph     │    │    │
                │   │   │                              │    │    │
                │   │   │  Fetch → Analyze (parallel) │    │    │
                │   │   │      → Aggregate → Dedup    │    │    │
                │   │   │      → Narrate → Publish    │    │    │
                │   │   └────────────┬────────────────┘    │    │
                │   │                ▼                      │    │
                │   │   ┌─────────────────────────────┐    │    │
                │   │   │  SignalBroadcaster (pubsub) │    │    │
                │   │   │  asyncio.Queue per client    │    │    │
                │   │   └────────────┬────────────────┘    │    │
                │   │                ▼                      │    │
                │   │   ┌─────────────────────────────┐    │    │
                │   │   │  WebSocket /ws endpoint      │    │    │
                │   │   │  + REST /api/signals (hist.) │    │    │
                │   │   │  + Static /  (dashboard)    │    │    │
                │   │   └────────────┬────────────────┘    │    │
                │   └────────────────┼─────────────────────┘    │
                │                    │                           │
                │   ┌────────────────▼─────────────────────┐    │
                │   │  SQLite on Railway Volume            │    │
                │   │  signals_history + dedup state       │    │
                │   └──────────────────────────────────────┘    │
                └────────────────┬─────────────────────────────┘
                                 │ HTTPS / WSS
                                 ▼
                       ┌──────────────────┐
                       │  Browser Client  │
                       │   (Dashboard)    │
                       └──────────────────┘
```

**עקרון מנחה:** ה-LLM **לא** מקבל החלטות מסחר. הוא רק מנסח. החלטות מבוססות-כללים בלבד (חיוני ל-backtesting, debugging, ואמון).

---

## Project Structure

```
g:\...\TEST\stock-signals-agent\
├── pyproject.toml
├── railway.json                  # Railway build/deploy config
├── Procfile                      # web: uvicorn src.main:app --host 0.0.0.0 --port $PORT
├── .env                          # MARKETDATA_TOKEN, ANTHROPIC_API_KEY, DATABASE_URL
├── .env.example
├── config\
│   ├── watchlist.yaml            # מניות + אינדיקטורים פעילים + thresholds
│   └── indicators.yaml           # פרמטרים גלובליים לאינדיקטורים
├── src\
│   ├── main.py                   # FastAPI app + scheduler lifespan
│   ├── graph\
│   │   ├── state.py              # SignalState (TypedDict)
│   │   ├── builder.py            # build_signal_graph()
│   │   └── nodes\
│   │       ├── fetch.py
│   │       ├── analyze.py        # parallel indicator dispatch
│   │       ├── aggregate.py
│   │       ├── dedup.py
│   │       ├── narrate.py
│   │       └── publish.py        # publishes to broadcaster + DB
│   ├── indicators\
│   │   ├── base.py               # Indicator ABC + registry
│   │   ├── momentum.py           # RSI, Stochastic
│   │   ├── trend.py              # MACD, EMA cross, ADX
│   │   ├── volatility.py         # Bollinger, ATR
│   │   └── volume.py             # OBV, VWAP
│   ├── data\
│   │   ├── provider.py           # DataProvider ABC
│   │   └── marketdata_app.py     # MarketDataAppProvider (aiohttp + cache + rate-limit)
│   ├── web\
│   │   ├── app.py                # FastAPI app factory + routes
│   │   ├── broadcaster.py        # in-process pubsub for signals
│   │   ├── ws.py                 # WebSocket endpoint
│   │   ├── api.py                # REST /api/signals, /api/symbols, /api/health
│   │   └── static\
│   │       ├── index.html        # dashboard
│   │       ├── app.js            # WS client + DOM rendering
│   │       └── style.css
│   ├── scheduler\
│   │   └── runner.py             # asyncio scheduler — tick per symbol
│   ├── storage\
│   │   └── db.py                 # SQLAlchemy — signal history + cooldown
│   └── utils\
│       ├── config.py             # load YAML
│       └── logging.py
├── tests\
│   ├── test_indicators.py
│   ├── test_aggregator.py
│   ├── test_graph_smoke.py
│   └── test_broadcaster.py
└── docs\
    ├── PLAN.md
    └── ARCHITECTURE.md
```

---

## Indicator Plugin System (לב המערכת)

זו הדרישה המרכזית — אינדיקטורים pluggable.

### `src/indicators/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
import pandas as pd

@dataclass
class IndicatorResult:
    name: str
    value: dict           # למשל {"rsi": 72.3}
    signal: str | None    # "BUY" / "SELL" / None
    strength: float       # 0..1
    reason: str           # "RSI=72.3 חצה 70 כלפי מעלה"

class Indicator(ABC):
    name: str             # "rsi"
    requires_columns: list[str] = ["close"]

    def __init__(self, **params): self.params = params

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> IndicatorResult: ...

_REGISTRY: dict[str, type[Indicator]] = {}

def register(cls: type[Indicator]):
    _REGISTRY[cls.name] = cls
    return cls

def build(name: str, **params) -> Indicator:
    return _REGISTRY[name](**params)

def available() -> list[str]:
    return list(_REGISTRY.keys())
```

### דוגמה — `src/indicators/momentum.py`

```python
import pandas_ta as ta
from .base import Indicator, IndicatorResult, register

@register
class RSI(Indicator):
    name = "rsi"

    def compute(self, df):
        period = self.params.get("period", 14)
        upper = self.params.get("upper", 70)
        lower = self.params.get("lower", 30)

        rsi = ta.rsi(df["close"], length=period)
        last, prev = rsi.iloc[-1], rsi.iloc[-2]

        signal, reason = None, f"RSI={last:.1f}"
        if prev < upper <= last:
            signal, reason = "SELL", f"RSI חצה {upper} כלפי מעלה ({last:.1f}) — Overbought"
        elif prev > lower >= last:
            signal, reason = "BUY", f"RSI חצה {lower} כלפי מטה ({last:.1f}) — Oversold"

        return IndicatorResult(
            name=self.name,
            value={"rsi": float(last)},
            signal=signal,
            strength=abs(last - 50) / 50,
            reason=reason,
        )
```

### קונפיגורציה — `config/watchlist.yaml`

```yaml
defaults:
  interval: "5min"
  cooldown_minutes: 60

symbols:
  - symbol: AAPL
    indicators:
      - { name: rsi,      period: 14, upper: 70, lower: 30 }
      - { name: macd,     fast: 12, slow: 26, signal: 9 }
      - { name: bbands,   period: 20, std: 2 }
      - { name: ema_cross, fast: 9, slow: 21 }

  - symbol: NVDA
    indicators:
      - { name: rsi }
      - { name: adx, period: 14, threshold: 25 }
      - { name: vwap }
```

**להוסיף אינדיקטור חדש:** קובץ אחד עם class חדש + `@register` + שורה ב-YAML. לא נוגעים בגרף, לא ב-aggregator, לא ב-broadcaster.

---

## LangGraph Design

### `src/graph/state.py`

```python
from typing import TypedDict, Annotated
import operator

class SignalState(TypedDict):
    symbol: str
    interval: str
    candles: object              # pd.DataFrame
    indicator_results: Annotated[list, operator.add]  # parallel-safe
    aggregated: dict | None      # {"action": "BUY", "score": 0.78, "components": [...]}
    suppressed: bool             # dedup result
    narration: str | None
    error: str | None
```

### Nodes

| Node | Tafkid | Tool calls |
|------|--------|-----------|
| **fetch** | מושך candles ל-state | `MarketDataAppProvider.get_candles(symbol, interval)` |
| **analyze** | בונה indicator instances מ-YAML, מריץ `compute()` במקביל | indicator registry |
| **aggregate** | סופר BUY vs SELL, משקלל לפי `strength`, יוצר `action` רק אם רוב מובהק + ≥2 אינדיקטורים מסכימים | פונקציה נטו |
| **dedup** | בודק ב-DB אם נשלח signal זהה ב-cooldown window | `storage.db` |
| **narrate** | קורא ל-Claude עם prompt מובנה — 2-3 משפטים בעברית | Anthropic SDK |
| **publish** | רושם ב-DB + מפיץ ל-broadcaster (כל ה-WebSocket clients מקבלים) | `web.broadcaster` |

### Conditional Edges
- `aggregate → dedup` תמיד
- `dedup → narrate` אם `aggregated and not suppressed`, אחרת `→ END`

### Parallel Indicators
LangGraph `Send` API — כל אינדיקטור = `Send("compute_one", {"indicator": cfg, "candles": ...})`. מצטרפים חזרה דרך `Annotated[list, operator.add]`.

---

## Web Layer

### FastAPI App — `src/web/app.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.init()
    scheduler_task = asyncio.create_task(scheduler.run_forever())
    yield
    # Shutdown
    scheduler_task.cancel()
    await db.close()

app = FastAPI(lifespan=lifespan)
app.include_router(api.router, prefix="/api")
app.include_router(ws.router)
app.mount("/", StaticFiles(directory="src/web/static", html=True))
```

### Broadcaster — `src/web/broadcaster.py`

In-memory pub/sub. כל WebSocket client מקבל `asyncio.Queue` משלו. `publish` node דוחף signal אחד → broadcaster משכפל לכל ה-queues.

```python
class SignalBroadcaster:
    def __init__(self):
        self._subscribers: set[asyncio.Queue] = set()

    async def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q): self._subscribers.discard(q)

    async def publish(self, signal: dict):
        for q in self._subscribers:
            try: q.put_nowait(signal)
            except asyncio.QueueFull: pass  # slow client — drop
```

### WebSocket Endpoint — `src/web/ws.py`

- חיבור: `wss://{app}.railway.app/ws`
- on-connect: שולח snapshot של 50 signals אחרונים מ-DB
- ואז streams signals חדשים בזמן אמת
- heartbeat ping כל 30 שניות

### REST Endpoints — `src/web/api.py`

| Method | Path | Tafkid |
|--------|------|--------|
| GET | `/api/health` | health check ל-Railway |
| GET | `/api/signals?symbol=&since=` | היסטוריה מ-DB |
| GET | `/api/symbols` | רשימת המניות הפעילות מ-YAML |
| GET | `/api/state/{symbol}` | last indicator values per symbol |

### Dashboard — `src/web/static/index.html`

Vanilla HTML + JS, ללא framework:
- **Live ticker** למעלה — signals שזורמים פנימה
- **Signal table** היסטוריה עם filter לפי symbol/action/timeframe
- **Per-symbol cards** — מצב עדכני של כל אינדיקטור (gauge / sparkline)
- WebSocket reconnect אוטומטי עם exponential backoff
- ללא תלות חיצונית חוץ מ-CSS (אולי Pico.css או Tailwind via CDN)

---

## Data Provider — marketdata.app

```python
# src/data/provider.py
class DataProvider(ABC):
    @abstractmethod
    async def get_candles(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame: ...
```

מימוש `MarketDataAppProvider`:
- `aiohttp` ל-async REST
- **Endpoint:** `GET https://api.marketdata.app/v1/stocks/candles/{resolution}/{symbol}/`
- **Auth:** `Authorization: Bearer ${MARKETDATA_TOKEN}`
- **Cache TTL** = `interval/2` (חוסך 50% quota כשמספר אינדיקטורים שואלים אותו symbol באותה דקה)
- **Rate limiter** (asyncio Semaphore + token bucket) — תקרת safety של 8 calls/min (מתוך 10K/יום)
- **Retry** עם exponential backoff על 5xx

החלפה ל-Alpaca/Polygon/Finnhub = class חדש שמממש את אותו ABC. אפס שינוי בשאר המערכת.

---

## Storage — SQLite (with Postgres upgrade path)

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,         -- BUY / SELL
    score REAL NOT NULL,
    interval TEXT NOT NULL,
    components_json TEXT NOT NULL,
    narration TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signals_symbol_time ON signals(symbol, created_at);
CREATE INDEX idx_signals_created    ON signals(created_at);
```

- **MVP:** SQLite על Railway Volume (mount path: `/data/signals.db`).
- **Upgrade path:** SQLAlchemy → `DATABASE_URL` env var → להחליף ל-`postgres://...` של Railway (חינמי) באפס שינוי בקוד.

**Dedup:** signal נחסם אם קיים signal זהה (אותו symbol + action) ב-`cooldown_minutes` האחרונות. מונע ספאם כשהאינדיקטור מתנדנד סביב סף.

---

## Scheduler — `src/scheduler/runner.py`

asyncio loop פנימי, לא APScheduler (מספיק):

```python
async def run_forever():
    while True:
        symbols = load_watchlist()
        await asyncio.gather(*[
            run_signal_graph(symbol) for symbol in symbols
        ], return_exceptions=True)
        await asyncio.sleep(60)  # interval
```

עם `Semaphore` להגביל concurrency (לא יותר מ-5 graph runs במקביל, להגן על quota).

---

## Dependencies — `pyproject.toml`

```toml
[project]
name = "stock-signals-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "websockets>=13.0",
    "langgraph>=0.2.0",
    "langchain-anthropic>=0.2.0",
    "anthropic>=0.40.0",
    "pandas>=2.2",
    "pandas-ta>=0.3.14b",
    "aiohttp>=3.9",
    "sqlalchemy[asyncio]>=2.0",
    "aiosqlite>=0.20",
    "asyncpg>=0.29",            # for future Postgres upgrade
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.24", "ruff>=0.6"]
```

---

## Deployment — Railway

### `railway.json`

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "uvicorn src.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/health",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

### Volume

Railway → Storage tab → New Volume:
- Mount path: `/data`
- Size: 1 GB (זול)
- `DATABASE_URL=sqlite+aiosqlite:////data/signals.db`

### Env Vars (Railway Dashboard)

| Var | Value |
|-----|-------|
| `MARKETDATA_TOKEN` | token מ-marketdata.app |
| `ANTHROPIC_API_KEY` | API key |
| `DATABASE_URL` | `sqlite+aiosqlite:////data/signals.db` |
| `LOG_LEVEL` | `INFO` |
| `WATCHLIST_PATH` | `/app/config/watchlist.yaml` |

### Auto-deploy

Railway מתחבר ל-GitHub repo → כל push ל-`main` deploys אוטומטית. URL ציבורי: `https://stock-signals-agent.up.railway.app`.

---

## שלבי מימוש (Implementation Phases)

| # | Phase | Deliverable | Verification |
|---|-------|-------------|--------------|
| 1 | **Skeleton** | מבנה תיקיות + pyproject + .env.example + railway.json | `pip install -e .` עובד; `python -c "import src"` ירוק |
| 2 | **DataProvider** | `MarketDataAppProvider` + cache + rate-limiter + tests | `await provider.get_candles("AAPL","5")` מחזיר DataFrame תקין |
| 3 | **Indicator framework** | base.py + RSI, MACD + registry + unit tests עם fixtures | `pytest tests/test_indicators.py` ירוק |
| 4 | **שאר האינדיקטורים** | BBANDS, EMA cross, ADX, ATR, Stochastic, OBV, VWAP | test per indicator |
| 5 | **LangGraph nodes** | fetch → analyze → aggregate → dedup, dry-run | `python -m src.cli.run_once AAPL` מדפיס aggregated |
| 6 | **Narrator (Claude)** | prompt template + node | smoke test |
| 7 | **Web layer** | FastAPI + WebSocket + Broadcaster + static dashboard | פתיחת `http://localhost:8000/` ושליחה ידנית של signal לדמו → מופיע בדפדפן |
| 8 | **Scheduler integration** | asyncio runner + lifespan + multi-symbol | רץ 30 דק' עם 3 מניות, מעקב quota usage |
| 9 | **Storage + Dedup** | SQLAlchemy models, signals table, dedup logic | test_dedup ירוק |
| 10 | **Railway deploy** | railway.json + Volume + env vars + GitHub connect | URL ציבורי פעיל, dashboard נטען |
| 11 | **Production hardening** | retries, circuit breaker, structured logging, /health | chaos test |

---

## Critical Files Reference

- [src/indicators/base.py](src/indicators/base.py) — ABC + registry
- [src/graph/builder.py](src/graph/builder.py) — `build_signal_graph()`
- [src/graph/nodes/analyze.py](src/graph/nodes/analyze.py) — parallel `Send` dispatch
- [src/data/marketdata_app.py](src/data/marketdata_app.py) — provider + rate limiter + cache
- [src/web/app.py](src/web/app.py) — FastAPI factory
- [src/web/broadcaster.py](src/web/broadcaster.py) — pub/sub
- [src/web/static/index.html](src/web/static/index.html) — dashboard
- [src/scheduler/runner.py](src/scheduler/runner.py) — asyncio loop
- [config/watchlist.yaml](config/watchlist.yaml) — קובץ העריכה של המשתמש
- [railway.json](railway.json) — deployment config

---

## Verification — End-to-End

1. **Indicator correctness:** unit tests עם candles מ-CSV ידוע + ערכי RSI/MACD ידועים → assert קרוב.
2. **Graph smoke:** mock provider מחזיר candles שמייצרים BUY → `aggregated.action == "BUY"`.
3. **Dedup:** הרצה כפולה → `suppressed=True` בשנייה.
4. **WebSocket:** פתיחת 2 browser tabs → signal אחד מגיע ל-2 שניהם.
5. **Local end-to-end:** `uvicorn src.main:app` → לחיצה על `/api/test/fire-signal` (dev-only) → ההודעה מופיעה בדשבורד.
6. **Railway deploy:** push ל-main → URL חי, dashboard נטען, ה-scheduler רץ.
7. **24h soak:** 5 מניות, מעקב metrics (quota, latency, errors, signals/יום).

---

## Open Questions (לסיבוב הבא — Phase 2+)

1. **Anthropic model:** Sonnet 4.6 או Haiku 4.5 ל-narration? המלצה: Haiku.
2. **Auth ל-dashboard:** כרגע פתוח. בעתיד — Basic Auth או JWT?
3. **Postgres migration:** מתי להחליף את SQLite ל-Postgres של Railway? המלצה: כשנגיע ל-100K signals או מעבר ל-multi-user.
4. **Backtesting & alerts על performance:** Phase 3.
5. **Mobile UX:** dashboard responsive או PWA?
