"""Typed Pydantic payloads — the contract agents build and validate.

Each agent constructs one of these models, writes its own role-scoped rows to PostgreSQL
through the Repository (see agents/persistence.py), then emits a CompletionSignal to the
Orchestrator. The Orchestrator coordinates lifecycle and assembles the report by reading
the agreed tables — it no longer relays raw payloads as a persistence pipe.
(Constitution v2.0.0, Principle II — Contracted Agent Boundaries.)
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
AnalysisPhase = Literal["static", "delivery"]


class SlideAnalysisPayload(BaseModel):
    slide_index: int = Field(ge=1)
    playbook_factor: int = Field(ge=1, le=12)
    finding_type: FindingType
    description: str
    suggested_fix: str = ""
    analysis_phase: AnalysisPhase = "static"


class SlideFindings(BaseModel):
    findings: list[SlideAnalysisPayload]


class SlideAnalysisBundle(BaseModel):
    session_id: uuid.UUID
    findings: list[SlideAnalysisPayload]
    slides_raw_text: list[dict]  # [{"slide_index": int, "text": str}]


# ── Content ───────────────────────────────────────────────────────────
class ContentFinding(BaseModel):
    type: Literal["FACTUAL_ERROR", "COVERAGE_GAP", "STRENGTH"]
    message: str
    context_quote: str = ""


class ContentResult(BaseModel):
    content_score: int = Field(ge=0, le=100)
    findings: list[ContentFinding]


class ContentAnalysisPayload(BaseModel):
    session_id: uuid.UUID
    topic: str
    content_score: float = Field(ge=0, le=100)
    findings: list[ContentFinding]
    research_status: Literal["full", "partial", "skipped", "not_applicable"] = "not_applicable"


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
    content_research_status: Literal["full", "partial", "skipped", "not_applicable"] = "not_applicable"
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


# ── Completion signal (agent → Orchestrator) ──────────────────────────
CompletionKind = Literal["VIDEO", "AUDIO", "PPTX", "CONTENT", "REPORT"]


class CompletionSignal(BaseModel):
    """Emitted by an agent AFTER its write commits (durability before notify).

    Advisory coordination only — the data already lives in the agreed tables; the
    Orchestrator reads the tables, not this payload.
    """

    session_id: uuid.UUID
    kind: CompletionKind
    meta: dict | None = None


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
