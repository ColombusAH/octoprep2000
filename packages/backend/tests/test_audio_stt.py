from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from agents.audio_agent import AudioAgent


@dataclass
class _SttSettings:
    stt_fallback_enabled: bool = True
    use_direct_providers: bool = False
    litellm_stt_model: str = "eleven-scribe-v1"


class _FakeOrchestrator:
    async def notify_complete(self, session_id, kind, meta=None):
        return None


class _FakeTranscriptResponse:
    text = "gateway text"


class _FakeTranscriptions:
    def __init__(self, calls: list[str], should_fail: bool) -> None:
        self.calls = calls
        self.should_fail = should_fail

    async def create(self, **kwargs):
        self.calls.append("gateway")
        if self.should_fail:
            raise RuntimeError("gateway unavailable")
        return _FakeTranscriptResponse()


class _FakeAudio:
    def __init__(self, calls: list[str], should_fail: bool) -> None:
        self.transcriptions = _FakeTranscriptions(calls, should_fail)


class _FakeClient:
    def __init__(self, calls: list[str], gateway_should_fail: bool) -> None:
        self.audio = _FakeAudio(calls, gateway_should_fail)


class _DirectAudioAgent(AudioAgent):
    def __init__(self, calls: list[str], direct_should_fail: bool) -> None:
        super().__init__(uuid.uuid4(), _FakeOrchestrator())
        self.calls = calls
        self.direct_should_fail = direct_should_fail

    async def _transcribe_direct_elevenlabs(self, wav_bytes: bytes) -> str:
        self.calls.append("direct")
        if self.direct_should_fail:
            raise RuntimeError("direct unavailable")
        return "direct text"


@pytest.mark.asyncio
async def test_stt_gateway_first_falls_back_to_direct(monkeypatch):
    calls: list[str] = []
    settings = _SttSettings(use_direct_providers=False)
    monkeypatch.setattr("agents.audio_agent.get_settings", lambda: settings)
    monkeypatch.setattr("agents.llm.get_settings", lambda: settings)
    monkeypatch.setattr("agents.audio_agent.get_llm", lambda: _FakeClient(calls, True))
    agent = _DirectAudioAgent(calls, direct_should_fail=False)

    text = await agent._transcribe(b"pcm")

    assert text == "direct text"
    assert calls == ["gateway", "direct"]


@pytest.mark.asyncio
async def test_stt_direct_first_falls_back_to_gateway(monkeypatch):
    calls: list[str] = []
    settings = _SttSettings(use_direct_providers=True)
    monkeypatch.setattr("agents.audio_agent.get_settings", lambda: settings)
    monkeypatch.setattr("agents.llm.get_settings", lambda: settings)
    monkeypatch.setattr("agents.audio_agent.get_llm", lambda: _FakeClient(calls, False))
    agent = _DirectAudioAgent(calls, direct_should_fail=True)

    text = await agent._transcribe(b"pcm")

    assert text == "gateway text"
    assert calls == ["direct", "gateway"]
