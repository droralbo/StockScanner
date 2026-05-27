# Stock Signals Agent

Agentic stock-signals system: LangGraph orchestrates fetch → indicator analysis → aggregation → narration → live broadcast. Watchlist & indicators driven by YAML; results pushed in real-time to a web dashboard via WebSocket. Designed to run on Railway.

See [docs/PLAN.md](docs/PLAN.md) for full architecture.

## Quick start (local)

```bash
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # Linux/Mac

pip install -e ".[dev]"

cp .env.example .env           # then fill MARKETDATA_TOKEN and ANTHROPIC_API_KEY

uvicorn src.main:app --reload --port 8000
```

Open `http://localhost:8000` — dashboard loads, WebSocket connects, signals stream in as the scheduler ticks.

## Run tests

```bash
pytest -v
```

## Configure watchlist

Edit [config/watchlist.yaml](config/watchlist.yaml). Add a symbol or indicator — no code change needed.

To add a brand-new indicator type:

1. Create class in `src/indicators/<group>.py` with `@register`
2. Add `name: your_indicator` under any symbol in `watchlist.yaml`
3. Restart server

## Deploy to Railway

1. Push the repo to GitHub.
2. New Railway project → Deploy from GitHub.
3. Add a Volume mounted at `/data` (1 GB).
4. Set env vars: `MARKETDATA_TOKEN`, `ANTHROPIC_API_KEY`, `DATABASE_URL=sqlite+aiosqlite:////data/signals.db`.
5. Generate public domain — dashboard is live.
