from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from agents.audio_agent import AudioAgent
from agents.schemas import AudioWarningPayload, TranscriptPayload


@dataclass
class _AudioAgentSettings:
    demo_replay: bool = False
    audio_chunk_seconds: int = 2


class _FakeOrchestrator:
    async def notify_complete(self, session_id, kind, meta=None):
        return None


class _RecordingAudioAgent(AudioAgent):
    def __init__(self, transcript: str) -> None:
        super().__init__(uuid.uuid4(), _FakeOrchestrator())
        self.transcript = transcript
        self.events: list[tuple[str, TranscriptPayload | AudioWarningPayload]] = []

    async def _transcribe(self, pcm_bytes: bytes) -> str:
        return self.transcript

    async def _write_transcript(self, payload: TranscriptPayload) -> None:
        self.events.append(("transcript", payload))

    async def _write_warning(self, payload: AudioWarningPayload) -> None:
        self.events.append(("warning", payload))


@pytest.mark.asyncio
async def test_push_chunk_writes_transcript_before_derived_warning(monkeypatch):
    monkeypatch.setattr("agents.audio_agent.get_settings", lambda: _AudioAgentSettings())
    agent = _RecordingAudioAgent("um hello everyone")

    await agent.push_chunk(b"pcm")

    assert [event_type for event_type, _ in agent.events] == ["transcript", "warning"]
    assert agent.events[0][1].filler_flags == ["um"]
    assert agent.events[1][1].event_type == "FILLER_WORDS"


@pytest.mark.asyncio
async def test_push_chunk_skips_empty_stt_output(monkeypatch):
    monkeypatch.setattr("agents.audio_agent.get_settings", lambda: _AudioAgentSettings())
    agent = _RecordingAudioAgent("   ")

    await agent.push_chunk(b"pcm")

    assert agent.events == []
