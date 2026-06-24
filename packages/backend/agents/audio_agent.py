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
from agents.persistence import AgentPersistence
from agents.replay_fixtures import replay_audio_events
from agents.schemas import AudioWarningPayload, TranscriptPayload
from config import get_settings
from core.feedback_broadcaster import broadcaster
from orchestrator.orchestrator import Orchestrator

FILLERS = {"um", "uh"}
FILLER_REGEX = re.compile(r"\b(" + "|".join(re.escape(w) for w in FILLERS) + r")\b", re.I)
AMBIGUOUS_FILLER_REGEX = re.compile(r"\blike\b", re.I)

WPM_HIGH = 160
WPM_LOW = 90
WPM_WINDOW_SECONDS = 30
WPM_MIN_EVIDENCE_SECONDS = 10
WARNING_DEBOUNCE_MS = 10_000


class AudioAgent(AgentPersistence):
    def __init__(
        self,
        session_id: uuid.UUID,
        orchestrator: Orchestrator,
        *,
        slide_state_provider=None,
    ) -> None:
        self.session_id = session_id
        self.orchestrator = orchestrator
        self._slide_state_provider = slide_state_provider
        self._session_started_ms = int(time.monotonic() * 1000)
        self._chunk_count = 0
        # rolling 30s window of (chunk_start_s, word_count)
        self._wpm_window: deque[tuple[float, int]] = deque()
        self._last_warning_by_type: dict[str, int] = {}
        self._replay_dispatched = False
        self._last_warning_ts = 0
        self._last_stale_slide_index: int | None = None

    # ── This agent owns transcript + audio_warning writes (Principle II) ──
    async def _write_transcript(self, payload: TranscriptPayload) -> None:
        await self._with_repo(
            lambda r: r.insert_transcript_entry(
                session_id=payload.session_id,
                start_ms=payload.start_ms,
                end_ms=payload.end_ms,
                text=payload.text,
                filler_flags=payload.filler_flags or None,
            )
        )
        await self.orchestrator.notify_complete(self.session_id, "AUDIO")

    async def _write_warning(self, payload: AudioWarningPayload) -> None:
        await self._with_repo(
            lambda r: r.insert_audio_warning(
                session_id=payload.session_id,
                timestamp_ms=payload.timestamp_ms,
                event_type=payload.event_type,
                severity=payload.severity,
                message=payload.message,
            )
        )
        await broadcaster.publish(
            payload.session_id,
            {
                "type": payload.event_type,
                "severity": payload.severity,
                "message": payload.message,
                "timestamp_ms": payload.timestamp_ms,
            },
        )
        await self.orchestrator.notify_complete(self.session_id, "AUDIO")

    async def push_chunk(self, pcm_bytes: bytes) -> None:
        if get_settings().demo_replay:
            if self._replay_dispatched:
                return
            self._replay_dispatched = True
            for ev in replay_audio_events(self.session_id):
                if isinstance(ev, TranscriptPayload):
                    await self._write_transcript(ev)
                elif isinstance(ev, AudioWarningPayload):
                    await self._write_warning(ev)
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

        fillers = _detect_fillers(text)
        await self._write_transcript(
            TranscriptPayload(
                session_id=self.session_id,
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
                filler_flags=fillers,
            )
        )

        if fillers and self._should_emit_warning("FILLER_WORDS", start_ms):
            await self._write_warning(
                AudioWarningPayload(
                    session_id=self.session_id,
                    timestamp_ms=start_ms,
                    event_type="FILLER_WORDS",
                    severity="LOW",
                    message=f"Filler word: {fillers[0]}",
                )
            )

        await self._update_wpm(text, end_ms)
        await self._check_stale_slide(end_ms)

    async def _check_stale_slide(self, ts_ms: int) -> None:
        if not self._slide_state_provider:
            return
        state = self._slide_state_provider(ts_ms)
        if not state:
            return

        threshold_ms = get_settings().stale_slide_seconds * 1000
        if state["dwell_ms"] < threshold_ms:
            return

        slide_index = state["slide_index"]
        if self._last_stale_slide_index == slide_index and ts_ms - self._last_warning_ts < threshold_ms:
            return
        if ts_ms - self._last_warning_ts < 60_000:
            return

        self._last_warning_ts = ts_ms
        self._last_stale_slide_index = slide_index
        minutes = max(1, state["dwell_ms"] // 60_000)
        await self._write_warning(
            AudioWarningPayload(
                session_id=self.session_id,
                timestamp_ms=ts_ms,
                event_type="STALE_SLIDE",
                severity="MEDIUM",
                message=(
                    f"You've been on slide {slide_index} for over {minutes} minute"
                    f"{'' if minutes == 1 else 's'} — consider advancing or wrapping up."
                ),
                metadata={"slide_index": slide_index, "dwell_ms": state["dwell_ms"]},
            )
        )

    async def _update_wpm(self, text: str, ts_ms: int) -> None:
        words = len(text.split())
        now_s = ts_ms / 1000
        chunk_start_s = max(0.0, now_s - get_settings().audio_chunk_seconds)
        self._wpm_window.append((chunk_start_s, words))
        cutoff = now_s - WPM_WINDOW_SECONDS
        while self._wpm_window and self._wpm_window[0][0] < cutoff:
            self._wpm_window.popleft()
        if not self._wpm_window:
            return
        if now_s < WPM_MIN_EVIDENCE_SECONDS:
            return
        total_words = sum(w for _, w in self._wpm_window)
        span = max(1.0, now_s - self._wpm_window[0][0])
        wpm = total_words * 60 / span

        if wpm > WPM_HIGH:
            if not self._should_emit_warning("PACING_TOO_FAST", ts_ms):
                return
            await self._write_warning(
                AudioWarningPayload(
                    session_id=self.session_id,
                    timestamp_ms=ts_ms,
                    event_type="PACING_TOO_FAST",
                    severity="MEDIUM",
                    message=f"Speaking too fast ({int(wpm)} WPM)",
                )
            )
        elif wpm < WPM_LOW:
            if not self._should_emit_warning("PACING_TOO_SLOW", ts_ms):
                return
            await self._write_warning(
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

    def _should_emit_warning(self, event_type: str, ts_ms: int) -> bool:
        last_ts = self._last_warning_by_type.get(event_type)
        if last_ts is not None and ts_ms - last_ts < WARNING_DEBOUNCE_MS:
            return False
        self._last_warning_by_type[event_type] = ts_ms
        return True


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


def _detect_fillers(text: str) -> list[str]:
    fillers = [m.group(0).lower() for m in FILLER_REGEX.finditer(text)]
    ambiguous = [m.group(0).lower() for m in AMBIGUOUS_FILLER_REGEX.finditer(text)]
    if len(ambiguous) > 1:
        fillers.extend(ambiguous)
    return fillers
