"""WS /slide-stream?session_id=X&token=Y — browser → backend, JSON slide-change events."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import ValidationError

from agents.schemas import SlideEventPayload
from db.repository import PostgreSQLRepository, get_repo
from middleware.session_auth import validate_ws_token
from runtime import registry

router = APIRouter()


@router.websocket("/slide-stream")
async def slide_stream(
    ws: WebSocket,
    session_id: uuid.UUID,
    token: str,
    repo: PostgreSQLRepository = Depends(get_repo),
):
    if not await validate_ws_token(session_id, token, repo):
        await ws.close(code=4003)
        return

    session = await repo.get_session(session_id)
    if not session or not session.pptx_ready or not session.slides_raw_text:
        await ws.close(code=4000)
        return

    slide_count = len(session.slides_raw_text)

    await ws.accept()
    rt = await registry.get_or_create(session_id)
    assert rt.pptx is not None
    logger.info("slide WS connected for {} ({} slides)", session_id, slide_count)

    event_count = 0
    try:
        while True:
            raw = await ws.receive_text()
            try:
                payload = SlideEventPayload.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning("invalid slide event for {}: {}", session_id, exc)
                continue

            if payload.slide_index > slide_count:
                logger.warning(
                    "slide index {} out of range 1..{} for {}",
                    payload.slide_index,
                    slide_count,
                    session_id,
                )
                continue

            accepted = await rt.pptx.record_slide_event(payload, slide_count=slide_count)
            if accepted:
                event_count += 1
    except WebSocketDisconnect:
        logger.info("slide WS closed for {} after {} events", session_id, event_count)
