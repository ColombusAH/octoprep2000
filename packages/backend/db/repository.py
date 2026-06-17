from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Report, Session, SlideAnalysis, TranscriptEntry, VideoEvent
from db.session import get_db


class PostgreSQLRepository:
    """Sole writer to PostgreSQL. Called by Orchestrator (writes) + Report/Content agents (reads)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Sessions ──────────────────────────────────────────────────────
    async def create_session(self, topic: str, topic_context: str | None = None) -> Session:
        session = Session(topic=topic, topic_context=topic_context)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: uuid.UUID | str) -> Session | None:
        sid = uuid.UUID(str(session_id)) if not isinstance(session_id, uuid.UUID) else session_id
        result = await self.db.execute(select(Session).where(Session.session_id == sid))
        return result.scalar_one_or_none()

    async def set_session_status(self, session_id: uuid.UUID, status: str) -> None:
        session = await self.get_session(session_id)
        if session:
            session.status = status
            await self.db.commit()

    async def mark_pptx_ready(self, session_id: uuid.UUID, slides_raw: list[dict[str, Any]]) -> None:
        session = await self.get_session(session_id)
        if session:
            session.pptx_ready = True
            session.slides_raw_text = slides_raw
            await self.db.commit()

    # ── Transcript ────────────────────────────────────────────────────
    async def insert_transcript_entry(
        self,
        session_id: uuid.UUID,
        start_ms: int,
        end_ms: int,
        text: str,
        filler_flags: list[str] | None,
    ) -> None:
        entry = TranscriptEntry(
            session_id=session_id,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
            filler_flags=filler_flags,
        )
        self.db.add(entry)
        await self.db.commit()

    async def read_transcript(self, session_id: uuid.UUID) -> list[TranscriptEntry]:
        result = await self.db.execute(
            select(TranscriptEntry)
            .where(TranscriptEntry.session_id == session_id)
            .order_by(TranscriptEntry.start_ms)
        )
        return list(result.scalars().all())

    # ── Video Events (batched insert per §10b.5) ──────────────────────
    async def bulk_insert_video_events(self, events: Iterable[dict[str, Any]]) -> None:
        for ev in events:
            self.db.add(VideoEvent(**ev))
        await self.db.commit()

    async def read_video_events(self, session_id: uuid.UUID) -> list[VideoEvent]:
        result = await self.db.execute(
            select(VideoEvent)
            .where(VideoEvent.session_id == session_id)
            .order_by(VideoEvent.timestamp_ms)
        )
        return list(result.scalars().all())

    # ── Slide Analysis ────────────────────────────────────────────────
    async def insert_slide_analyses(self, items: Iterable[dict[str, Any]]) -> None:
        for it in items:
            self.db.add(SlideAnalysis(**it))
        await self.db.commit()

    async def read_slide_analyses(self, session_id: uuid.UUID) -> list[SlideAnalysis]:
        result = await self.db.execute(
            select(SlideAnalysis)
            .where(SlideAnalysis.session_id == session_id)
            .order_by(SlideAnalysis.slide_index)
        )
        return list(result.scalars().all())

    # ── Report ────────────────────────────────────────────────────────
    async def insert_report(self, payload: dict[str, Any]) -> Report:
        report = Report(**payload)
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_report_by_session(self, session_id: uuid.UUID) -> Report | None:
        result = await self.db.execute(select(Report).where(Report.session_id == session_id))
        return result.scalar_one_or_none()

    async def set_report_share_token(self, session_id: uuid.UUID, token: uuid.UUID) -> None:
        report = await self.get_report_by_session(session_id)
        if report:
            report.share_token = token
            await self.db.commit()


async def get_repo(db: AsyncSession = Depends(get_db)) -> PostgreSQLRepository:
    return PostgreSQLRepository(db)
