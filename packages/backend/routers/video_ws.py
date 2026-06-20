"""WS /video-stream?session_id=X&token=Y — browser → backend, binary JPEG frames."""

from __future__ import annotations

from loguru import logger
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from db.repository import PostgreSQLRepository, get_repo
from middleware.session_auth import validate_ws_token
from runtime import registry

router = APIRouter()


@router.websocket("/video-stream")
async def video_stream(
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
    if rt.orchestrator.is_fallback(session_id):
        await ws.close(code=1000)
        return

    logger.info("video WS connected for {}", session_id)
    frame_count = 0
    try:
        while True:
            frame = await ws.receive_bytes()
            frame_count += 1
            if frame_count % 10 == 1:
                logger.info("video frame #{} ({} bytes) for {}", frame_count, len(frame), session_id)
            assert rt.frame_service is not None
            await rt.frame_service.ingest(frame)
    except WebSocketDisconnect:
        logger.info("video WS closed for {} after {} frames", session_id, frame_count)
