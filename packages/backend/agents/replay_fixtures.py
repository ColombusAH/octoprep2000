"""DEMO_MODE=replay — load canned event fixtures instead of calling live APIs.

Per FR-010a + §10b.2. Dev 5 owns. Team Lead flips DEMO_MODE only if live APIs flake.
Fixtures cover Vision frame events, Audio chunks, PPTX slide findings, Content findings.
"""

from __future__ import annotations

import json
import uuid
from functools import lru_cache
from pathlib import Path

from agents.schemas import (
    AudioWarningPayload,
    ContentAnalysisPayload,
    ContentFinding,
    SlideAnalysisPayload,
    TranscriptPayload,
    VideoEventPayload,
)

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@lru_cache(maxsize=8)
def _load(name: str):
    path = FIXTURE_DIR / name
    if not path.exists():
        return None
    return json.loads(path.read_text())


def replay_vision_events(session_id: uuid.UUID) -> list[VideoEventPayload]:
    out: list[VideoEventPayload] = []
    for raw in _load("vision_events.json") or []:
        try:
            out.append(VideoEventPayload(session_id=session_id, **raw))
        except Exception:  # noqa: BLE001
            continue
    return out


def replay_audio_events(
    session_id: uuid.UUID,
    speech_language: str = "en",
) -> list[TranscriptPayload | AudioWarningPayload]:
    fixture_name = "audio_events_he.json" if speech_language == "he" else "audio_events.json"
    out: list[TranscriptPayload | AudioWarningPayload] = []
    for cached_raw in _load(fixture_name) or []:
        raw = dict(cached_raw)
        kind = raw.pop("kind", "transcript")
        try:
            if kind == "transcript":
                out.append(TranscriptPayload(session_id=session_id, **raw))
            else:
                out.append(AudioWarningPayload(session_id=session_id, **raw))
        except Exception:  # noqa: BLE001
            continue
    return out


def replay_slide_findings() -> list[SlideAnalysisPayload]:
    out: list[SlideAnalysisPayload] = []
    for raw in _load("slide_findings.json") or []:
        try:
            out.append(SlideAnalysisPayload(**raw))
        except Exception:  # noqa: BLE001
            continue
    return out


def replay_delivery_findings() -> list[SlideAnalysisPayload]:
    out: list[SlideAnalysisPayload] = []
    for raw in _load("slide_delivery_findings.json") or []:
        try:
            out.append(SlideAnalysisPayload(**raw))
        except Exception:  # noqa: BLE001
            continue
    return out


def replay_slide_events() -> list:
    """Canned slide timeline for DEMO_MODE=replay delivery pass."""
    out: list = []
    for raw in _load("slide_events.json") or []:
        try:
            out.append(type("SlideEventStub", (), raw)())
        except Exception:  # noqa: BLE001
            continue
    return out


def replay_content_analysis(session_id: uuid.UUID, topic: str) -> ContentAnalysisPayload:
    data = _load("content_findings.json") or {}
    findings: list[ContentFinding] = []
    for raw in data.get("findings", []):
        try:
            findings.append(ContentFinding(**raw))
        except Exception:  # noqa: BLE001
            continue
    return ContentAnalysisPayload(
        session_id=session_id,
        topic=topic,
        content_score=float(data.get("content_score", 0)),
        findings=findings,
        research_status="not_applicable",
    )
