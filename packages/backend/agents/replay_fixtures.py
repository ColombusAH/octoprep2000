"""DEMO_MODE=replay — load canned event fixtures instead of calling live APIs.

Per FR-010a + §10b.2. Dev 5 owns. Team Lead flips DEMO_MODE only if live APIs flake.
"""

from __future__ import annotations

import json
import uuid
from functools import lru_cache
from pathlib import Path

from agents.schemas import AudioWarningPayload, TranscriptPayload, VideoEventPayload

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@lru_cache(maxsize=2)
def _load(name: str) -> list[dict]:
    path = FIXTURE_DIR / name
    if not path.exists():
        return []
    return json.loads(path.read_text())


def replay_vision_events(session_id: uuid.UUID) -> list[VideoEventPayload]:
    out: list[VideoEventPayload] = []
    for raw in _load("vision_events.json"):
        try:
            out.append(VideoEventPayload(session_id=session_id, **raw))
        except Exception:  # noqa: BLE001
            continue
    return out


def replay_audio_events(
    session_id: uuid.UUID,
) -> list[TranscriptPayload | AudioWarningPayload]:
    out: list[TranscriptPayload | AudioWarningPayload] = []
    for raw in _load("audio_events.json"):
        kind = raw.pop("kind", "transcript")
        try:
            if kind == "transcript":
                out.append(TranscriptPayload(session_id=session_id, **raw))
            else:
                out.append(AudioWarningPayload(session_id=session_id, **raw))
        except Exception:  # noqa: BLE001
            continue
    return out
