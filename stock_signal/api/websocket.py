import json
import logging
from typing import Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)

_connections: Set[WebSocket] = set()


async def connect(ws: WebSocket) -> None:
    await ws.accept()
    _connections.add(ws)
    logger.info("WebSocket client connected (%d total)", len(_connections))


def disconnect(ws: WebSocket) -> None:
    _connections.discard(ws)
    logger.info("WebSocket client disconnected (%d total)", len(_connections))


async def broadcast(payload: dict) -> None:
    dead = set()
    message = json.dumps(payload)
    for ws in _connections:
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _connections.discard(ws)
