from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from agents.audio_agent import AudioAgent
from agents.schemas import AudioWarningPayload, TranscriptPayload


@dataclass
class _LiveWarningSettings:
    demo_replay: bool = False
    audio_chunk_seconds: int = 2


class _FakeOrchestrator:
    async def notify_complete(self, session_id, kind, meta=None):
        return None


class _RecordingAudioAgent(AudioAgent):
    def __init__(self) -> None:
        super().__init__(uuid.uuid4(), _FakeOrchestrator())
        self.transcripts: list[TranscriptPayload] = []
        self.warnings: list[AudioWarningPayload] = []

    async def _transcribe(self, pcm_bytes: bytes) -> str:
        return "um hello"

    async def _write_transcript(self, payload: TranscriptPayload) -> None:
        self.transcripts.append(payload)

    async def _write_warning(self, payload: AudioWarningPayload) -> None:
        self.warnings.append(payload)


@pytest.mark.asyncio
async def test_repeated_filler_live_warnings_are_throttled_without_suppressing_transcripts(
    monkeypatch,
):
    monkeypatch.setattr("agents.audio_agent.get_settings", lambda: _LiveWarningSettings())
    agent = _RecordingAudioAgent()

    await agent.push_chunk(b"first")
    await agent.push_chunk(b"second")

    assert len(agent.transcripts) == 2
    assert [warning.event_type for warning in agent.warnings] == ["FILLER_WORDS"]
