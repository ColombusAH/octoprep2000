from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from agents.audio_agent import AudioAgent
from agents.schemas import AudioWarningPayload


@dataclass
class _PacingSettings:
    audio_chunk_seconds: int = 2


class _FakeOrchestrator:
    async def notify_complete(self, session_id, kind, meta=None):
        return None


class _RecordingAudioAgent(AudioAgent):
    def __init__(self) -> None:
        super().__init__(uuid.uuid4(), _FakeOrchestrator())
        self.warnings: list[AudioWarningPayload] = []

    async def _write_warning(self, payload: AudioWarningPayload) -> None:
        self.warnings.append(payload)


@pytest.mark.asyncio
async def test_pacing_does_not_warn_before_minimum_evidence_window(monkeypatch):
    monkeypatch.setattr("agents.audio_agent.get_settings", lambda: _PacingSettings())
    agent = _RecordingAudioAgent()

    for ts_ms in (2000, 4000, 6000, 8000):
        await agent._update_wpm("one two three four five six seven eight nine ten", ts_ms)

    assert agent.warnings == []


@pytest.mark.asyncio
async def test_pacing_detects_sustained_fast_ten_second_segment(monkeypatch):
    monkeypatch.setattr("agents.audio_agent.get_settings", lambda: _PacingSettings())
    agent = _RecordingAudioAgent()

    for ts_ms in (2000, 4000, 6000, 8000, 10000):
        await agent._update_wpm("one two three four five six seven eight nine ten", ts_ms)

    assert [warning.event_type for warning in agent.warnings] == ["PACING_TOO_FAST"]


@pytest.mark.asyncio
async def test_pacing_debounces_repeated_warnings(monkeypatch):
    monkeypatch.setattr("agents.audio_agent.get_settings", lambda: _PacingSettings())
    agent = _RecordingAudioAgent()

    for ts_ms in (2000, 4000, 6000, 8000, 10000, 12000):
        await agent._update_wpm("one two three four five six seven eight nine ten", ts_ms)

    assert len(agent.warnings) == 1
