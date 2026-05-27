import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.utils.logging import get_logger

log = get_logger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def signals_ws(ws: WebSocket):
    await ws.accept()
    broadcaster = ws.app.state.broadcaster
    store = ws.app.state.store

    queue = await broadcaster.subscribe()
    try:
        # send snapshot of recent history on connect
        history = await store.recent_signals(limit=50)
        await ws.send_text(json.dumps({"type": "snapshot", "signals": history}))

        async def receiver():
            """Drain client messages so disconnects are detected promptly."""
            while True:
                await ws.receive_text()

        async def sender():
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30)
                    await ws.send_text(json.dumps({"type": "signal", "signal": msg}))
                except asyncio.TimeoutError:
                    await ws.send_text(json.dumps({"type": "ping"}))

        await asyncio.gather(receiver(), sender())

    except WebSocketDisconnect:
        log.info("websocket disconnected")
    except Exception as e:
        log.warning("websocket error: %s", e)
    finally:
        await broadcaster.unsubscribe(queue)
