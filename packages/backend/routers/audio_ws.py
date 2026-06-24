"""WS /audio-stream?session_id=X&token=Y — browser → backend, binary PCM chunks."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from loguru import logger

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
    if not await validate_ws_token(session_id, token, repo, require_active=True):
        await ws.close(code=4003)
        return

    await ws.accept()
    rt = await registry.get_or_create(session_id)
    logger.info("audio WS connected for {}", session_id)

    chunk_count = 0
    try:
        while True:
            chunk = await ws.receive_bytes()
            if not await repo.is_session_active(session_id):
                await ws.close(code=4003)
                return
            chunk_count += 1
            logger.info("audio chunk #{} ({} bytes) for {}", chunk_count, len(chunk), session_id)
            assert rt.aggregator is not None
            # Each 2s chunk closes a live window (frames buffered since last chunk + this
            # chunk) and fires one LiveSessionWorkflow run — does not block this receive loop.
            await rt.aggregator.add_chunk(chunk)
    except WebSocketDisconnect:
        logger.info("audio WS closed for {} after {} chunks", session_id, chunk_count)
