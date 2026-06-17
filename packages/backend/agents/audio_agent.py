"""AudioAgent — ElevenLabs Scribe v1 STT + filler/WPM detection.

2-second PCM 16kHz chunks (NFR-002 reconciliation, v1.4).
Emits TranscriptPayload + optional AudioWarningPayload to Orchestrator.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections import deque

import httpx

from agents.replay_fixtures import replay_audio_events
from agents.schemas import AudioWarningPayload, TranscriptPayload
from config import get_settings
from orchestrator.agno_orchestrator import AgnoOrchestrator

logger = logging.getLogger(__name__)

FILLERS = {"um", "uh", "ah", "hmm", "like", "you know", "kinda", "sorta"}
FILLER_REGEX = re.compile(r"\b(" + "|".join(re.escape(w) for w in FILLERS) + r")\b", re.I)

WPM_HIGH = 160
WPM_LOW = 90
WPM_WINDOW_SECONDS = 30
ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"


class AudioAgent:
    def __init__(self, session_id: uuid.UUID, orchestrator: AgnoOrchestrator) -> None:
        self.session_id = session_id
        self.orchestrator = orchestrator
        self._session_started_ms = int(time.monotonic() * 1000)
        self._chunk_count = 0
        # rolling 30s window of (timestamp_s, word_count)
        self._wpm_window: deque[tuple[float, int]] = deque()
        self._last_warning_ts = 0
        self._http = httpx.AsyncClient(timeout=10.0)

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
            logger.exception("STT failed: %s", exc)
            return

        if not text.strip():
            return

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
        files = {"file": ("chunk.wav", pcm_bytes, "audio/wav")}
        data = {"model_id": "scribe_v1"}
        resp = await self._http.post(
            ELEVENLABS_STT_URL,
            files=files,
            data=data,
            headers={"xi-api-key": s.elevenlabs_api_key},
        )
        resp.raise_for_status()
        return resp.json().get("text", "")

    async def aclose(self) -> None:
        await self._http.aclose()
