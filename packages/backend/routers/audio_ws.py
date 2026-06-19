"""WS /audio-stream?session_id=X&token=Y — browser → backend, binary PCM chunks."""

from __future__ import annotations

from loguru import logger
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from db.repository import PostgreSQLRepository, get_repo
from middleware.session_auth import validate_ws_token
from runtime import registry

router = APIRouter()


@router.websocket("/audio-stream")
async def audio_stream(
    ws: WebSocket,
    session_id: uuid.UUID,
    token: str,
    repo: PostgreSQLRepository = Depends(get_repo),
):
    if not await validate_ws_token(session_id, token, repo):
        await ws.close(code=4003)
        return

    await ws.accept()
    rt = await registry.get_or_create(session_id)

    try:
        while True:
            chunk = await ws.receive_bytes()
            assert rt.audio is not None
            await rt.audio.push_chunk(chunk)
    except WebSocketDisconnect:
        logger.info("audio WS closed for {}", session_id)
