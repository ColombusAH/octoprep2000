from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    access_token: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, default=uuid.uuid4
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    topic_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    pptx_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    slides_raw_text: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    transcript_entries: Mapped[list["TranscriptEntry"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    video_events: Mapped[list["VideoEvent"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    audio_warnings: Mapped[list["AudioWarning"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    slide_analyses: Mapped[list["SlideAnalysis"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    slide_events: Mapped[list["SlideEvent"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    report: Mapped["Report | None"] = relationship(
        back_populates="session", cascade="all, delete-orphan", uselist=False
    )


class TranscriptEntry(Base):
    __tablename__ = "transcript_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), index=True
    )
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    filler_flags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    session: Mapped[Session] = relationship(back_populates="transcript_entries")


class VideoEvent(Base):
    __tablename__ = "video_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), index=True
    )
    timestamp_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    raw_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    session: Mapped[Session] = relationship(back_populates="video_events")


class AudioWarning(Base):
    __tablename__ = "audio_warnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), index=True
    )
    timestamp_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    session: Mapped[Session] = relationship(back_populates="audio_warnings")


class SlideEvent(Base):
    __tablename__ = "slide_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), index=True
    )
    slide_index: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, server_default="manual")

    session: Mapped[Session] = relationship(back_populates="slide_events")


class SlideAnalysis(Base):
    __tablename__ = "slide_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), index=True
    )
    slide_index: Mapped[int] = mapped_column(Integer, nullable=False)
    playbook_factor: Mapped[int] = mapped_column(Integer, nullable=False)
    finding_type: Mapped[str] = mapped_column(String(16), nullable=False)  # STRENGTH | IMPROVEMENT
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_fix: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    analysis_phase: Mapped[str] = mapped_column(String(16), nullable=False, server_default="static")

    session: Mapped[Session] = relationship(back_populates="slide_analyses")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    voice_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    slide_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    content_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    content_research_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    insights: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    mentor_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    share_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    session: Mapped[Session] = relationship(back_populates="report")
