"""In-process pub/sub: maps session_id → set of subscribed WebSockets.

Per architecture decision (C4 §10): no Redis. Single FastAPI process, asyncio-only.
"""

from __future__ import annotations

import asyncio
from loguru import logger
import uuid
from typing import Any

from fastapi import WebSocket



class FeedbackBroadcaster:
    def __init__(self) -> None:
        self._subs: dict[uuid.UUID, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def register(self, session_id: uuid.UUID, ws: WebSocket) -> None:
        async with self._lock:
            self._subs.setdefault(session_id, set()).add(ws)
        logger.info("WS subscribed: session=%s total=%d", session_id, len(self._subs[session_id]))

    async def unregister(self, session_id: uuid.UUID, ws: WebSocket) -> None:
        async with self._lock:
            subs = self._subs.get(session_id)
            if subs:
                subs.discard(ws)
                if not subs:
                    self._subs.pop(session_id, None)

    async def publish(self, session_id: uuid.UUID, payload: dict[str, Any]) -> None:
        subs = list(self._subs.get(session_id, ()))
        dead: list[WebSocket] = []
        for ws in subs:
            try:
                await ws.send_json(payload)
            except Exception as exc:  # noqa: BLE001
                logger.warning("WS send failed (%s); marking dead", exc)
                dead.append(ws)
        for ws in dead:
            await self.unregister(session_id, ws)


# Singleton — imported by routers + orchestrator
broadcaster = FeedbackBroadcaster()
