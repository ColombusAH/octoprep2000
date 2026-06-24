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
import time
import uuid
from collections import deque

from loguru import logger

from agents import face_detection
from agents.llm import (
    call_with_fallback,
    encode_image_b64,
    encode_image_b64_raw,
    get_anthropic_llm,
    get_llm,
    pick_provider_order,
)
from agents.persistence import AgentPersistence
from agents.replay_fixtures import replay_vision_events
from agents.schemas import VideoEventPayload
from config import get_settings
from core.feedback_broadcaster import broadcaster
from orchestrator.orchestrator import Orchestrator

BATCH_SIZE = 3
# Video-event writes are batched by THIS agent (Constitution v2.0.0, §10b.5):
# flush every 1s OR when the buffer reaches N=20.
VIDEO_BUFFER_MAX = 20
VIDEO_FLUSH_INTERVAL_S = 1.0
SYSTEM_PROMPT = """You are a body language coach reviewing a live presenter from camera frames.
Your job is to detect posture and gesture issues using the Tikal Presentation Skills Playbook as your standard.

## Rubric (Tikal Presentation Skills Playbook — body language section)
- Open positions are correct: chest directed at the audience, arms and hands open or behind the back.
- Closed/nervous signals are problems: scratching head or neck, hands joined in front, hunched shoulders.
- Movement is positive — it attracts focus and keeps the presenter sharp.
  Flag POSTURE_ISSUE only for rigid, locked, or collapsed posture — not for natural movement.
- Speaking with hands is encouraged when gestures are intentional.
  Flag GESTURE_CLOSED only when arms are consistently crossed or tucked tightly against the body.
- The presenter should face the audience. Flag OUT_OF_FRAME when they are consistently
  sideways or turned away from the camera.

## What NOT to do
- Do NOT emit EYE_CONTACT_LOST or FACE_NOT_DETECTED — those are handled by upstream Google Vision.
- Do not flag natural hand gestures as problems — only flag when arms are closed or absent.
- Do not emit duplicate events for the same issue across consecutive frames — wait for a change.

## Output format
Reply with a JSON object:
{"events": [{"type": str, "severity": "LOW|MEDIUM|HIGH", "message": str}]}
Allowed type values: POSTURE_ISSUE, OUT_OF_FRAME, GESTURE_CLOSED.
Only emit an event when confident. Empty events list is valid.

## Examples of good events
{"type": "POSTURE_ISSUE", "severity": "MEDIUM",
 "message": "Shoulders are hunched and chest is turned away — open up toward the audience."}

{"type": "GESTURE_CLOSED", "severity": "LOW",
 "message": "Arms crossed in front for an extended period — try open hands or hands behind back."}

{"type": "OUT_OF_FRAME", "severity": "HIGH",
 "message": "Presenter is consistently turned sideways — face the camera to face your audience."}"""


class VisionAgent(AgentPersistence):
    def __init__(self, session_id: uuid.UUID, orchestrator: Orchestrator) -> None:
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
        # This agent owns video_events writes (Principle II): buffer + batched flush.
        self._video_buffer: list[dict] = []
        self._flush_task: asyncio.Task = asyncio.create_task(self._periodic_flush())

    # ── video_events: own buffer, batched write, live publish, completion ──
    async def _emit_event(self, payload: VideoEventPayload) -> None:
        self._video_buffer.append(
            {
                "session_id": payload.session_id,
                "timestamp_ms": payload.timestamp_ms,
                "event_type": payload.event_type,
                "severity": payload.severity,
                "raw_metadata": payload.raw_metadata,
            }
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
        if len(self._video_buffer) >= VIDEO_BUFFER_MAX:
            await self.flush()

    async def flush(self) -> None:
        """Persist buffered video events, then signal completion (durability before notify)."""
        if not self._video_buffer:
            return
        events, self._video_buffer = self._video_buffer, []
        try:
            await self._with_repo(lambda r: r.bulk_insert_video_events(events))
            await self.orchestrator.notify_complete(
                self.session_id, "VIDEO", {"events_flushed": len(events)}
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("video_events flush failed: {}", exc)

    async def _periodic_flush(self) -> None:
        while True:
            await asyncio.sleep(VIDEO_FLUSH_INTERVAL_S)
            await self.flush()

    async def aclose(self) -> None:
        """Cancel the periodic flush and persist any remaining buffered events."""
        self._flush_task.cancel()
        await self.flush()

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
        await self._emit_event(payload)

    # ── LLM layer (posture / gestures only) ──────────────────────────
    async def _analyse(self, frames: list[bytes]) -> None:
        if get_settings().demo_replay:
            for ev in replay_vision_events(self.session_id):
                await self._emit_event(ev)
            return

        s = get_settings()

        async def _gateway() -> dict:
            return await self._call_gateway(frames)

        async def _claude() -> dict:
            return await self._call_claude(frames)

        claude_fn = _claude if s.fallback_enabled else None
        primary, secondary = pick_provider_order(claude_fn, _gateway)
        try:
            result = await asyncio.wait_for(
                call_with_fallback(primary, secondary),
                timeout=self._timeout_ms / 1000,
            )
            self._timeout_streak = 0
        except TimeoutError:
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
            await self._emit_event(payload)

    async def _call_gateway(self, frames: list[bytes]) -> dict:
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
        parsed = json.loads(resp.choices[0].message.content or "{}")
        logger.info("Vision LLM result: {} event(s) {}", len(parsed.get("events", [])), parsed.get("events"))
        return parsed

    async def _call_claude(self, frames: list[bytes]) -> dict:
        s = get_settings()
        client = get_anthropic_llm()
        content: list[dict] = [{"type": "text", "text": "Evaluate these 3 frames as a sequence."}]
        for f in frames:
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": encode_image_b64_raw(f)},
                }
            )
        resp = await client.messages.create(
            model=s.anthropic_model,
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text.strip() or "{}")
        logger.info(
            "Vision Claude fallback result: {} event(s) {}", len(parsed.get("events", [])), parsed.get("events")
        )
        return parsed

    def _now_ms(self) -> int:
        return int(time.monotonic() * 1000) - self._session_started_ms
