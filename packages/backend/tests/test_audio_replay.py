from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from agents.audio_agent import AudioAgent
from agents.schemas import AudioWarningPayload, TranscriptPayload


@dataclass
class _ReplaySettings:
    demo_replay: bool = True


class _FakeOrchestrator:
    async def notify_complete(self, session_id, kind, meta=None):
        return None


class _RecordingAudioAgent(AudioAgent):
    def __init__(self, session_id: uuid.UUID) -> None:
        super().__init__(session_id, _FakeOrchestrator())
        self.transcripts: list[TranscriptPayload] = []
        self.warnings: list[AudioWarningPayload] = []

    async def _write_transcript(self, payload: TranscriptPayload) -> None:
        self.transcripts.append(payload)

    async def _write_warning(self, payload: AudioWarningPayload) -> None:
        self.warnings.append(payload)


@pytest.mark.asyncio
async def test_demo_replay_dispatches_audio_events_once_per_agent_session(monkeypatch):
    session_id = uuid.uuid4()
    events = [
        TranscriptPayload(session_id=session_id, start_ms=0, end_ms=2000, text="um hello"),
        AudioWarningPayload(
            session_id=session_id,
            timestamp_ms=0,
            event_type="FILLER_WORDS",
            severity="LOW",
            message="Filler word: um",
        ),
    ]
    monkeypatch.setattr("agents.audio_agent.get_settings", lambda: _ReplaySettings())
    monkeypatch.setattr("agents.audio_agent.replay_audio_events", lambda _session_id: events)

    agent = _RecordingAudioAgent(session_id)

    await agent.push_chunk(b"first")
    await agent.push_chunk(b"second")

    assert agent.transcripts == [events[0]]
    assert agent.warnings == [events[1]]
