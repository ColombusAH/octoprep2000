"""VisionAgent — hybrid pipeline: GCV face_detection (fast, deterministic) + GPT-4o (semantic).

Pipeline per kept frame (post-imagehash dedup):
  1. Run GCV face_detection on the latest frame (asyncio.to_thread). Cheap, deterministic.
     - empty faces        → emit FACE_NOT_DETECTED
     - |pan| or |tilt| > θ → emit EYE_CONTACT_LOST
     - |roll| > θ          → emit FACE_TILTED
     - joy LIKELY/V_LIKELY → emit SMILING_STRONG (STRENGTH signal for Report)
  2. Buffer frames until BATCH_SIZE; flush to GPT-4o Vision for posture/gestures (semantic).
     - 3 consecutive LLM timeouts → Orchestrator.activate_fallback()

GCV preempts LLM for face checks → fewer LLM tokens + faster eye-contact latency.
"""

from __future__ import annotations

import asyncio
import json
from loguru import logger
import time
import uuid
from collections import deque

from agents import face_detection
from agents.llm import encode_image_b64, get_llm
from agents.replay_fixtures import replay_vision_events
from agents.schemas import VideoEventPayload
from config import get_settings
from orchestrator.agno_orchestrator import AgnoOrchestrator


BATCH_SIZE = 3
SYSTEM_PROMPT = """You evaluate a presenter's body language from camera frames.
Reply with a JSON object: {"events": [{"type": str, "severity": "LOW|MEDIUM|HIGH", "message": str}]}
Allowed type values: POSTURE_ISSUE, OUT_OF_FRAME, GESTURE_CLOSED.
NOTE: face/eye-contact already covered by upstream Google Vision face detection — do NOT emit
EYE_CONTACT_LOST or FACE_NOT_DETECTED. Focus only on body posture and gestures.
Only emit an event when confident. Empty events list is valid."""


class VisionAgent:
    def __init__(self, session_id: uuid.UUID, orchestrator: AgnoOrchestrator) -> None:
        self.session_id = session_id
        self.orchestrator = orchestrator
        self._frame_buf: deque[bytes] = deque(maxlen=BATCH_SIZE)
        self._session_started_ms = int(time.monotonic() * 1000)
        self._timeout_streak = 0
        self._last_event_type: str | None = None
        self._last_face_event: str | None = None
        self._timeout_ms = get_settings().vision_timeout_ms
        # GCV rate limit — cap to ~1 fps to keep cost bounded (NFR-004)
        self._gcv_min_interval_ms = 1000
        self._gcv_last_ms = -10_000

    async def push_frame(self, frame_bytes: bytes) -> None:
        # GCV face detection runs at most once per second (cost cap, NFR-004).
        now_ms = int(time.monotonic() * 1000)
        if now_ms - self._gcv_last_ms >= self._gcv_min_interval_ms:
            self._gcv_last_ms = now_ms
            asyncio.create_task(self._run_face_detection(frame_bytes))

        self._frame_buf.append(frame_bytes)
        if len(self._frame_buf) >= BATCH_SIZE:
            frames = list(self._frame_buf)
            self._frame_buf.clear()
            await self._analyse(frames)

    # ── GCV layer ────────────────────────────────────────────────────
    async def _run_face_detection(self, frame_bytes: bytes) -> None:
        if get_settings().demo_replay or not face_detection.is_enabled():
            return
        metrics = await face_detection.detect(frame_bytes)
        if metrics is None:
            return

        ts = self._now_ms()

        if metrics.face_count == 0:
            await self._emit_face_event(
                "FACE_NOT_DETECTED",
                "MEDIUM",
                "Face not detected in frame",
                ts,
                metrics,
            )
            return

        if face_detection.is_eye_contact_lost(metrics):
            await self._emit_face_event(
                "EYE_CONTACT_LOST",
                "HIGH",
                "Look back at the camera",
                ts,
                metrics,
            )
            return  # do not stack with other face events

        if face_detection.is_head_tilted(metrics):
            await self._emit_face_event(
                "FACE_TILTED",
                "LOW",
                "Straighten your head",
                ts,
                metrics,
            )
            return

        if face_detection.is_smiling_strong(metrics):
            await self._emit_face_event(
                "SMILING_STRONG",
                "LOW",
                "Great smile — keep it up",
                ts,
                metrics,
            )

    async def _emit_face_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        ts: int,
        metrics: face_detection.FaceMetrics,
    ) -> None:
        if event_type == self._last_face_event:
            return  # dedupe consecutive identical face events
        self._last_face_event = event_type
        try:
            payload = VideoEventPayload(
                session_id=self.session_id,
                timestamp_ms=ts,
                event_type=event_type,  # type: ignore[arg-type]
                severity=severity,  # type: ignore[arg-type]
                message=message,
                raw_metadata={
                    "source": "google_vision",
                    "pan_deg": metrics.pan_deg,
                    "tilt_deg": metrics.tilt_deg,
                    "roll_deg": metrics.roll_deg,
                    "joy": metrics.joy,
                    "confidence": metrics.detection_confidence,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("invalid face payload {} skipped: {}", event_type, exc)
            return
        await self.orchestrator.on_video_event(payload)

    # ── LLM layer (posture / gestures only) ──────────────────────────
    async def _analyse(self, frames: list[bytes]) -> None:
        if get_settings().demo_replay:
            for ev in replay_vision_events(self.session_id):
                await self.orchestrator.on_video_event(ev)
            return

        try:
            result = await asyncio.wait_for(self._call_llm(frames), timeout=self._timeout_ms / 1000)
            self._timeout_streak = 0
        except (TimeoutError, asyncio.TimeoutError):
            self._timeout_streak += 1
            logger.warning("Vision LLM timeout {}/3", self._timeout_streak)
            if self._timeout_streak >= 3:
                await self.orchestrator.activate_fallback(self.session_id)
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("Vision LLM call failed: {}", exc)
            return

        ts = self._now_ms()
        for raw in result.get("events", []):
            event_type = raw.get("type")
            if event_type == self._last_event_type:
                continue
            try:
                payload = VideoEventPayload(
                    session_id=self.session_id,
                    timestamp_ms=ts,
                    event_type=event_type,
                    severity=raw.get("severity", "MEDIUM"),
                    message=raw.get("message", ""),
                    raw_metadata={"source": "gpt4o_vision"},
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("invalid LLM payload skipped: {} ({})", raw, exc)
                continue
            self._last_event_type = event_type
            await self.orchestrator.on_video_event(payload)

    async def _call_llm(self, frames: list[bytes]) -> dict:
        s = get_settings()
        client = get_llm()
        content: list[dict] = [{"type": "text", "text": "Evaluate these 3 frames as a sequence."}]
        for f in frames:
            content.append({"type": "image_url", "image_url": {"url": encode_image_b64(f)}})
        resp = await client.chat.completions.create(
            model=s.litellm_vision_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            response_format={"type": "json_object"},
            max_tokens=400,
        )
        return json.loads(resp.choices[0].message.content or "{}")

    def _now_ms(self) -> int:
        return int(time.monotonic() * 1000) - self._session_started_ms
