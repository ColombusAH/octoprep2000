"""Central brain. Sole writer to PostgreSQL.

Receives typed Pydantic payloads from agents, validates, persists via Repository,
forwards warnings to the FeedbackBroadcaster.

Per §10b.5 — VideoEvent inserts are batched (every 1s OR N=20).
Per §6 (open decision 4) — Agno is brand-tax. If Agno PoC fails, replace inner
machinery with raw `asyncio.create_task`; this public API stays identical.

Lifecycle note (B2 fix): Orchestrator does NOT hold an AsyncSession. Each write
opens a fresh session via `get_session_maker()`. Survives request-scope teardown
because no DB handle is captured in instance state.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from agents.schemas import (
    AudioWarningPayload,
    ContentAnalysisPayload,
    ReportPayload,
    SlideAnalysisBundle,
    TranscriptPayload,
    VideoEventPayload,
)
from core.feedback_broadcaster import broadcaster
from db.repository import PostgreSQLRepository
from db.session import get_session_maker

VIDEO_BUFFER_MAX = 20
VIDEO_FLUSH_INTERVAL_S = 1.0


class Orchestrator:
    def __init__(self) -> None:
        self._video_buffer: dict[uuid.UUID, list[dict[str, Any]]] = {}
        self._tasks: dict[uuid.UUID, dict[str, asyncio.Task]] = {}
        self._fallback_active: set[uuid.UUID] = set()
        self._flush_task: asyncio.Task | None = None

    # ── DB write helper: fresh session per call ──────────────────────
    async def _with_repo(self, fn: Callable[[PostgreSQLRepository], Awaitable[Any]]) -> Any:
        async with get_session_maker()() as db:
            repo = PostgreSQLRepository(db)
            return await fn(repo)

    # ── Session lifecycle ────────────────────────────────────────────
    async def start_session(self, session_id: uuid.UUID) -> None:
        self._video_buffer.setdefault(session_id, [])
        self._tasks.setdefault(session_id, {})
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("Orchestrator: session {} started", session_id)

    async def end_session(self, session_id: uuid.UUID) -> None:
        for name, task in self._tasks.get(session_id, {}).items():
            task.cancel()
            logger.debug("cancelled task {} for {}", name, session_id)
        await self._flush_video_events(session_id)
        await self._with_repo(lambda r: r.set_session_status(session_id, "ENDED"))
        logger.info("Orchestrator: session {} ended", session_id)

    async def mark_report_ready(self, session_id: uuid.UUID) -> None:
        await self._with_repo(lambda r: r.set_session_status(session_id, "REPORT_READY"))
        await broadcaster.publish(
            session_id, {"type": "REPORT_READY", "session_id": str(session_id)}
        )

    # ── Agent payload entry points (validation wall) ─────────────────
    async def on_video_event(self, payload: VideoEventPayload) -> None:
        buf = self._video_buffer.setdefault(payload.session_id, [])
        buf.append(
            {
                "session_id": payload.session_id,
                "timestamp_ms": payload.timestamp_ms,
                "event_type": payload.event_type,
                "severity": payload.severity,
                "raw_metadata": payload.raw_metadata,
            }
        )
        await broadcaster.publish(
            payload.session_id,
            {
                "type": payload.event_type,
                "severity": payload.severity,
                "message": payload.message,
                "timestamp_ms": payload.timestamp_ms,
            },
        )
        if len(buf) >= VIDEO_BUFFER_MAX:
            await self._flush_video_events(payload.session_id)

    async def on_transcript(self, payload: TranscriptPayload) -> None:
        await self._with_repo(
            lambda r: r.insert_transcript_entry(
                session_id=payload.session_id,
                start_ms=payload.start_ms,
                end_ms=payload.end_ms,
                text=payload.text,
                filler_flags=payload.filler_flags or None,
            )
        )

    async def on_audio_warning(self, payload: AudioWarningPayload) -> None:
        await self._with_repo(
            lambda r: r.insert_audio_warning(
                session_id=payload.session_id,
                timestamp_ms=payload.timestamp_ms,
                event_type=payload.event_type,
                severity=payload.severity,
                message=payload.message,
            )
        )
        await broadcaster.publish(
            payload.session_id,
            {
                "type": payload.event_type,
                "severity": payload.severity,
                "message": payload.message,
                "timestamp_ms": payload.timestamp_ms,
            },
        )

    async def on_slide_analysis(self, bundle: SlideAnalysisBundle) -> None:
        async def write(repo: PostgreSQLRepository) -> None:
            await repo.insert_slide_analyses(
                [
                    {
                        "session_id": bundle.session_id,
                        "slide_index": f.slide_index,
                        "playbook_factor": f.playbook_factor,
                        "finding_type": f.finding_type,
                        "description": f.description,
                        "suggested_fix": f.suggested_fix,
                    }
                    for f in bundle.findings
                ]
            )
            await repo.mark_pptx_ready(bundle.session_id, bundle.slides_raw_text)

        await self._with_repo(write)

    async def on_content_analysis(self, payload: ContentAnalysisPayload) -> None:
        await broadcaster.publish(
            payload.session_id, {"type": "CONTENT_READY", "score": payload.content_score}
        )

    async def on_report(self, payload: ReportPayload) -> None:
        await self._with_repo(
            lambda r: r.insert_report(
                {
                    "session_id": payload.session_id,
                    "overall_score": payload.overall_score,
                    "voice_score": payload.voice_score,
                    "body_score": payload.body_score,
                    "slide_score": payload.slide_score,
                    "content_score": payload.content_score,
                    "insights": [i.model_dump() for i in payload.insights],
                    "mentor_unlocked": payload.mentor_unlocked,
                }
            )
        )
        await self.mark_report_ready(payload.session_id)

    # ── Audio-only fallback (§4c) ────────────────────────────────────
    async def activate_fallback(self, session_id: uuid.UUID) -> None:
        if session_id in self._fallback_active:
            return
        self._fallback_active.add(session_id)
        video_task = self._tasks.get(session_id, {}).pop("video", None)
        if video_task:
            video_task.cancel()
        await broadcaster.publish(
            session_id,
            {
                "type": "FALLBACK_ACTIVATED",
                "message": "Video analysis unavailable — continuing with audio coaching",
            },
        )

    def is_fallback(self, session_id: uuid.UUID) -> bool:
        return session_id in self._fallback_active

    # ── Internal: batched video event flush ──────────────────────────
    async def _flush_video_events(self, session_id: uuid.UUID) -> None:
        buf = self._video_buffer.get(session_id)
        if not buf:
            return
        events, self._video_buffer[session_id] = buf, []
        try:
            await self._with_repo(lambda r: r.bulk_insert_video_events(events))
        except Exception as exc:  # noqa: BLE001
            logger.exception("video_events flush failed: {}", exc)

    async def _periodic_flush(self) -> None:
        while True:
            await asyncio.sleep(VIDEO_FLUSH_INTERVAL_S)
            for sid in list(self._video_buffer.keys()):
                await self._flush_video_events(sid)

    def register_task(self, session_id: uuid.UUID, name: str, task: asyncio.Task) -> None:
        self._tasks.setdefault(session_id, {})[name] = task
