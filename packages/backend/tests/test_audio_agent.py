from __future__ import annotations

import uuid
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from agents.audio_agent import FILLER_REGEX, FILLER_REGEX_HE, AudioAgent, _detect_fillers
from agents.replay_fixtures import replay_audio_events
from agents.schemas import AudioWarningPayload, TranscriptPayload


@dataclass
class _AudioAgentSettings:
    demo_replay: bool = False
    audio_chunk_seconds: int = 2


class _FakeOrchestrator:
    async def notify_complete(self, session_id, kind, meta=None):
        return None


class _RecordingAudioAgent(AudioAgent):
    def __init__(self, transcript: str, speech_language: str = "en") -> None:
        super().__init__(uuid.uuid4(), _FakeOrchestrator(), speech_language=speech_language)
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


def test_hebrew_filler_detected_in_hebrew_sentence():
    text = "אז כאילו זה מעניין מאוד"
    matches = [m.group(0) for m in FILLER_REGEX_HE.finditer(text)]
    assert matches == ["כאילו"]


def test_english_filler_not_detected_by_hebrew_regex():
    text = "um yes like actually"
    assert list(FILLER_REGEX_HE.finditer(text)) == []


def test_english_filler_detected_by_english_regex():
    text = "um yes actually"
    matches = [m.group(0).lower() for m in FILLER_REGEX.finditer(text)]
    assert "um" in matches


def test_repeated_ambiguous_like_is_detected_for_english():
    assert _detect_fillers("like this is like important", "en") == ["like", "like"]


def test_hebrew_filler_not_detected_by_english_regex():
    text = "אז כאילו זה מעניין"
    assert list(FILLER_REGEX.finditer(text)) == []


@pytest.mark.parametrize(
    ("speech_language", "text", "expected"),
    [
        ("he", "אה זה טוב", ["אה"]),
        ("en", "um yes", ["um"]),
        ("he", "um yes", []),
        ("en", "אז כאילו", []),
    ],
)
def test_audio_agent_selects_lexicon_by_speech_language(
    speech_language: str, text: str, expected: list[str]
):
    agent = AudioAgent(uuid.uuid4(), MagicMock(), speech_language=speech_language)
    matches = [m.group(0).lower() for m in agent._filler_regex.finditer(text)]
    assert matches == expected


def test_replay_fixture_selects_hebrew_transcript_for_he_speech_language():
    session_id = uuid.uuid4()
    events = replay_audio_events(session_id, speech_language="he")
    transcripts = [e for e in events if isinstance(e, TranscriptPayload)]
    assert transcripts
    assert any("כאילו" in t.text for t in transcripts)
    assert all(t.session_id == session_id for t in transcripts)


def test_replay_fixture_uses_english_transcript_by_default():
    events = replay_audio_events(uuid.uuid4(), speech_language="en")
    transcripts = [e for e in events if isinstance(e, TranscriptPayload)]
    assert any("React 19" in t.text for t in transcripts)
