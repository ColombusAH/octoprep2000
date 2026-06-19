"""WS /realtime-feedback?session_id=X&token=Y — backend → browser pub/sub."""

from __future__ import annotations

import asyncio
from loguru import logger
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from core.feedback_broadcaster import broadcaster
from db.repository import PostgreSQLRepository, get_repo
from middleware.session_auth import validate_ws_token

router = APIRouter()


@router.websocket("/realtime-feedback")
async def feedback_stream(
    ws: WebSocket,
    session_id: uuid.UUID,
    token: str,
    repo: PostgreSQLRepository = Depends(get_repo),
):
    if not await validate_ws_token(session_id, token, repo):
        await ws.close(code=4003)
        return

    await ws.accept()
    await broadcaster.register(session_id, ws)
    try:
        # Keep the socket alive — outbound only. Use receive to detect disconnect.
        while True:
            await asyncio.wait_for(ws.receive_text(), timeout=60)
    except (WebSocketDisconnect, TimeoutError, asyncio.TimeoutError):
        pass
    finally:
        await broadcaster.unregister(session_id, ws)
        logger.info("feedback WS closed for %s", session_id)
