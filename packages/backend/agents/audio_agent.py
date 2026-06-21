"""AudioAgent — ElevenLabs Scribe v1 STT + filler/WPM detection.

2-second PCM 16kHz chunks (NFR-002 reconciliation, v1.4).
Browser sends raw PCM 16-bit mono. We wrap with a RIFF/WAVE header before
POST to Scribe — the API requires a real audio container, not raw samples.
Emits TranscriptPayload + optional AudioWarningPayload to Orchestrator.

When ELEVENLABS_API_KEY is set, a failed gateway transcription call falls back to
a direct (non-gateway) call against ElevenLabs' own API. PROVIDER_MODE=direct
flips the order so the direct call goes first. See agents.llm.pick_provider_order.
"""

from __future__ import annotations

import re
import struct
import time
import uuid
from collections import deque

import httpx
from loguru import logger

from agents.llm import call_with_fallback, get_llm, pick_provider_order
from agents.replay_fixtures import replay_audio_events
from agents.schemas import AudioWarningPayload, TranscriptPayload
from config import get_settings
from orchestrator.orchestrator import Orchestrator

FILLERS = {"um", "uh", "ah", "hmm", "like", "you know", "kinda", "sorta"}
FILLER_REGEX = re.compile(r"\b(" + "|".join(re.escape(w) for w in FILLERS) + r")\b", re.I)

WPM_HIGH = 160
WPM_LOW = 90
WPM_WINDOW_SECONDS = 30


class AudioAgent:
    def __init__(self, session_id: uuid.UUID, orchestrator: Orchestrator) -> None:
        self.session_id = session_id
        self.orchestrator = orchestrator
        self._session_started_ms = int(time.monotonic() * 1000)
        self._chunk_count = 0
        # rolling 30s window of (timestamp_s, word_count)
        self._wpm_window: deque[tuple[float, int]] = deque()
        self._last_warning_ts = 0

    async def push_chunk(self, pcm_bytes: bytes) -> None:
        if get_settings().demo_replay:
            for ev in replay_audio_events(self.session_id):
                if isinstance(ev, TranscriptPayload):
                    await self.orchestrator.on_transcript(ev)
                elif isinstance(ev, AudioWarningPayload):
                    await self.orchestrator.on_audio_warning(ev)
            return

        chunk_dur_ms = get_settings().audio_chunk_seconds * 1000
        start_ms = self._chunk_count * chunk_dur_ms
        end_ms = start_ms + chunk_dur_ms
        self._chunk_count += 1

        try:
            text = await self._transcribe(pcm_bytes)
        except Exception as exc:  # noqa: BLE001
            logger.exception("STT failed: {}", exc)
            return

        if not text.strip():
            logger.info("STT returned empty text for chunk {} ({} bytes PCM)", self._chunk_count, len(pcm_bytes))
            return

        logger.info("STT transcribed chunk {}: {!r}", self._chunk_count, text)

        fillers = [m.group(0).lower() for m in FILLER_REGEX.finditer(text)]
        await self.orchestrator.on_transcript(
            TranscriptPayload(
                session_id=self.session_id,
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
                filler_flags=fillers,
            )
        )

        if fillers:
            await self.orchestrator.on_audio_warning(
                AudioWarningPayload(
                    session_id=self.session_id,
                    timestamp_ms=start_ms,
                    event_type="FILLER_WORDS",
                    severity="LOW",
                    message=f"Filler word: {fillers[0]}",
                )
            )

        await self._update_wpm(text, end_ms)

    async def _update_wpm(self, text: str, ts_ms: int) -> None:
        words = len(text.split())
        now_s = ts_ms / 1000
        self._wpm_window.append((now_s, words))
        cutoff = now_s - WPM_WINDOW_SECONDS
        while self._wpm_window and self._wpm_window[0][0] < cutoff:
            self._wpm_window.popleft()
        if not self._wpm_window:
            return
        total_words = sum(w for _, w in self._wpm_window)
        span = max(1.0, now_s - self._wpm_window[0][0])
        wpm = total_words * 60 / span

        if ts_ms - self._last_warning_ts < 10_000:
            return  # debounce 10s

        if wpm > WPM_HIGH:
            self._last_warning_ts = ts_ms
            await self.orchestrator.on_audio_warning(
                AudioWarningPayload(
                    session_id=self.session_id,
                    timestamp_ms=ts_ms,
                    event_type="PACING_TOO_FAST",
                    severity="MEDIUM",
                    message=f"Speaking too fast ({int(wpm)} WPM)",
                )
            )
        elif wpm < WPM_LOW:
            self._last_warning_ts = ts_ms
            await self.orchestrator.on_audio_warning(
                AudioWarningPayload(
                    session_id=self.session_id,
                    timestamp_ms=ts_ms,
                    event_type="PACING_TOO_SLOW",
                    severity="LOW",
                    message=f"Speaking slowly ({int(wpm)} WPM)",
                )
            )

    async def _transcribe(self, pcm_bytes: bytes) -> str:
        s = get_settings()
        wav_bytes = _wrap_pcm_as_wav(pcm_bytes, sample_rate=16000, channels=1, bits_per_sample=16)
        client = get_llm()

        async def _gateway() -> str:
            resp = await client.audio.transcriptions.create(
                model=s.litellm_stt_model,
                file=("chunk.wav", wav_bytes, "audio/wav"),
            )
            return resp.text or ""

        async def _direct() -> str:
            return await self._transcribe_direct_elevenlabs(wav_bytes)

        direct_fn = _direct if s.stt_fallback_enabled else None
        primary, secondary = pick_provider_order(direct_fn, _gateway)
        return await call_with_fallback(primary, secondary)

    async def _transcribe_direct_elevenlabs(self, wav_bytes: bytes) -> str:
        s = get_settings()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={"xi-api-key": s.elevenlabs_api_key},
                data={"model_id": "scribe_v1"},
                files={"file": ("chunk.wav", wav_bytes, "audio/wav")},
            )
        resp.raise_for_status()
        return resp.json().get("text") or ""

    async def aclose(self) -> None:
        pass


def _wrap_pcm_as_wav(
    pcm_bytes: bytes,
    sample_rate: int,
    channels: int,
    bits_per_sample: int,
) -> bytes:
    """Prepend a RIFF/WAVE header so raw PCM is decodable as audio/wav.

    Scribe (and most audio APIs) require a real container — raw samples won't decode.
    Header is 44 bytes for PCM (format 1).
    """
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    subchunk2_size = len(pcm_bytes)
    chunk_size = 36 + subchunk2_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,             # subchunk1_size (PCM)
        1,              # audio_format (PCM)
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        subchunk2_size,
    )
    return header + pcm_bytes
