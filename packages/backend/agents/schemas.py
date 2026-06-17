"""Typed Pydantic payloads — only contract agents expose to the Orchestrator.

Agents NEVER write to the DB directly. They build one of these models in memory and
emit it upward via `Orchestrator.on_*`. The Orchestrator validates here and persists
via the Repository.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ── Vision ────────────────────────────────────────────────────────────
VideoEventType = Literal[
    "EYE_CONTACT_LOST",
    "POSTURE_ISSUE",
    "OUT_OF_FRAME",
    "GESTURE_CLOSED",
    "FACE_NOT_DETECTED",
    "FACE_TILTED",
    "SMILING_STRONG",
]
Severity = Literal["LOW", "MEDIUM", "HIGH"]


class VideoEventPayload(BaseModel):
    session_id: uuid.UUID
    timestamp_ms: int = Field(ge=0)
    event_type: VideoEventType
    severity: Severity
    message: str
    raw_metadata: dict | None = None


# ── Audio ─────────────────────────────────────────────────────────────
class TranscriptPayload(BaseModel):
    session_id: uuid.UUID
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str
    filler_flags: list[str] = Field(default_factory=list)


AudioWarningType = Literal[
    "FILLER_WORDS",
    "PACING_TOO_FAST",
    "PACING_TOO_SLOW",
    "STALE_SLIDE",
]


class AudioWarningPayload(BaseModel):
    session_id: uuid.UUID
    timestamp_ms: int = Field(ge=0)
    event_type: AudioWarningType
    severity: Severity
    message: str
    metadata: dict | None = None


# ── PPTX ──────────────────────────────────────────────────────────────
FindingType = Literal["STRENGTH", "IMPROVEMENT"]


class SlideAnalysisPayload(BaseModel):
    slide_index: int = Field(ge=1)
    playbook_factor: int = Field(ge=1, le=12)
    finding_type: FindingType
    description: str


class SlideAnalysisBundle(BaseModel):
    session_id: uuid.UUID
    findings: list[SlideAnalysisPayload]
    slides_raw_text: list[dict]  # [{"slide_index": int, "text": str}]


# ── Content ───────────────────────────────────────────────────────────
class ContentFinding(BaseModel):
    type: Literal["FACTUAL_ERROR", "COVERAGE_GAP", "STRENGTH"]
    message: str
    context_quote: str = ""


class ContentAnalysisPayload(BaseModel):
    session_id: uuid.UUID
    topic: str
    content_score: float = Field(ge=0, le=100)
    findings: list[ContentFinding]


# ── Report ────────────────────────────────────────────────────────────
InsightCategory = Literal["voice", "body", "slide", "content"]


class Insight(BaseModel):
    category: InsightCategory
    type: FindingType
    message: str
    timestamps: list[int] = Field(default_factory=list)
    slides: list[int] = Field(default_factory=list)


class ReportPayload(BaseModel):
    session_id: uuid.UUID
    overall_score: float = Field(ge=0, le=100)
    voice_score: float = Field(ge=0, le=100)
    body_score: float | None = Field(default=None, ge=0, le=100)
    slide_score: float = Field(ge=0, le=100)
    content_score: float = Field(ge=0, le=100)
    insights: list[Insight]

    @property
    def mentor_unlocked(self) -> bool:
        return self.overall_score >= 80

    @field_validator("insights")
    @classmethod
    def must_have_insights(cls, v: list[Insight]) -> list[Insight]:
        if not v:
            raise ValueError("Report must contain at least one insight")
        return v


# ── Request bodies ────────────────────────────────────────────────────
class CreateSessionBody(BaseModel):
    topic: str = Field(min_length=8, max_length=200)
    topic_context: str | None = Field(default=None, max_length=500)

    @field_validator("topic")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("topic cannot be blank")
        return v.strip()


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID
    access_token: uuid.UUID


# ── WS outbound payloads (to dashboard) ───────────────────────────────
class FeedbackEvent(BaseModel):
    type: str
    severity: Severity | None = None
    message: str | None = None
    timestamp_ms: int | None = None
    session_id: uuid.UUID | None = None
