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
from dataclasses import dataclass, field

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

# Span tracking: consecutive same-type detections within this gap are merged into ONE
# event row that carries a duration, instead of N near-duplicate point events. A live
# toast still fires the instant a span opens, so real-time coaching latency is unchanged.
SPAN_GAP_MS = 3000
_SEVERITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
# LLM may only emit these; face/eye types are owned by GCV upstream.
_LLM_EVENT_TYPES = {"POSTURE_ISSUE", "OUT_OF_FRAME", "GESTURE_CLOSED"}
# Peak (not last) is the useful summary for these angle metrics over a span.
_PEAK_ABS_KEYS = ("pan_deg", "tilt_deg", "roll_deg")


@dataclass
class _Span:
    """An open, ongoing body-language issue, keyed by event_type, accumulating duration."""

    event_type: str
    severity: str
    message: str
    start_ms: int
    last_ms: int
    count: int = 1
    metadata: dict = field(default_factory=dict)


def _merge_metadata(base: dict, new: dict | None) -> None:
    """Fold a new frame's metrics into the span. Head angles keep their peak magnitude
    (a 45° turn is worse than 16°); everything else takes the latest value."""
    for k, v in (new or {}).items():
        if k in _PEAK_ABS_KEYS and isinstance(v, (int, float)) and isinstance(base.get(k), (int, float)):
            if abs(v) > abs(base[k]):
                base[k] = v
        else:
            base[k] = v
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
        self._timeout_ms = get_settings().vision_timeout_ms
        # GCV rate limit — cap to ~1 fps to keep cost bounded (NFR-004)
        self._gcv_min_interval_ms = 1000
        self._gcv_last_ms = -10_000
        # Open issue spans, keyed by event_type (types are disjoint across GCV/LLM).
        # A span accumulates duration until a SPAN_GAP_MS quiet period or session end.
        self._spans: dict[str, _Span] = {}
        # True once any caller supplies a media-timeline ts (feature 003 batch path);
        # in that mode the wall-clock periodic sweep is disabled (it would mis-close spans).
        self._media_clock = False
        # This agent owns video_events writes (Principle II): buffer + batched flush.
        self._video_buffer: list[dict] = []
        self._flush_task: asyncio.Task = asyncio.create_task(self._periodic_flush())

    # ── live feedback (instant) vs. persistence (batched) ────────────
    async def _publish_live(self, event_type: str, severity: str, message: str, ts: int) -> None:
        """Real-time coaching toast — fired the instant an issue is first seen."""
        await broadcaster.publish(
            self.session_id,
            {"type": event_type, "severity": severity, "message": message, "timestamp_ms": ts},
        )

    async def _buffer_row(self, payload: VideoEventPayload) -> None:
        """Queue one durable video_events row. Duration + message + peak metrics ride in
        raw_metadata (JSONB) so no schema migration is needed for the richer signal."""
        meta = dict(payload.raw_metadata or {})
        meta.setdefault("message", payload.message)
        meta.setdefault("duration_ms", payload.duration_ms)
        if payload.end_ms is not None:
            meta.setdefault("end_ms", payload.end_ms)
        self._video_buffer.append(
            {
                "session_id": payload.session_id,
                "timestamp_ms": payload.timestamp_ms,
                "event_type": payload.event_type,
                "severity": payload.severity,
                "raw_metadata": meta,
            }
        )
        if len(self._video_buffer) >= VIDEO_BUFFER_MAX:
            await self.flush()

    async def _emit_event(self, payload: VideoEventPayload) -> None:
        """Back-compat single-shot emit (replay fixtures, direct callers): publish + persist."""
        await self._publish_live(
            payload.event_type, payload.severity, payload.message, payload.timestamp_ms
        )
        await self._buffer_row(payload)

    # ── span tracking: merge consecutive same-type detections by duration ──
    async def _observe(
        self, event_type: str, severity: str, message: str, ts: int, metadata: dict
    ) -> None:
        span = self._spans.get(event_type)
        if span is not None and ts - span.last_ms <= SPAN_GAP_MS:
            # Same ongoing issue — extend it. Keep the worst-moment severity + message,
            # and the peak head angles, as the representative summary for the report.
            span.last_ms = ts
            span.count += 1
            if _SEVERITY_RANK.get(severity, 2) > _SEVERITY_RANK.get(span.severity, 2):
                span.severity = severity
                span.message = message
            _merge_metadata(span.metadata, metadata)
            return
        if span is not None:
            await self._close_span(span)  # gap exceeded — close the stale span first
        self._spans[event_type] = _Span(
            event_type=event_type,
            severity=severity,
            message=message,
            start_ms=ts,
            last_ms=ts,
            metadata=dict(metadata),
        )
        # Issue just started → coach immediately; the durable row lands when it ends.
        await self._publish_live(event_type, severity, message, ts)

    async def _close_span(self, span: _Span) -> None:
        meta = dict(span.metadata)
        meta["count"] = span.count
        try:
            payload = VideoEventPayload(
                session_id=self.session_id,
                timestamp_ms=span.start_ms,
                end_ms=span.last_ms,
                event_type=span.event_type,  # type: ignore[arg-type]
                severity=span.severity,  # type: ignore[arg-type]
                message=span.message,
                raw_metadata=meta,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("invalid span {} skipped: {}", span.event_type, exc)
            return
        await self._buffer_row(payload)

    async def _sweep_spans(self, now_ms: int, *, force: bool = False) -> None:
        for etype in list(self._spans.keys()):
            span = self._spans[etype]
            if force or now_ms - span.last_ms > SPAN_GAP_MS:
                await self._close_span(span)
                del self._spans[etype]

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
            # Close spans that went quiet (live mode only — batch uses media time).
            if not self._media_clock:
                await self._sweep_spans(self._now_ms())
            await self.flush()

    async def aclose(self) -> None:
        """Cancel the periodic flush, close any open spans, and persist remaining events."""
        self._flush_task.cancel()
        await self._sweep_spans(0, force=True)
        await self.flush()

    async def on_frame_instant(self, frame_bytes: bytes, ts_ms: int | None = None) -> None:
        """Instant deterministic path — runs on frame ingest, NOT inside the agno window,
        so eye-contact/face cues keep sub-100ms latency. GCV is rate-limited to ~1 fps.

        `ts_ms` (feature 003 batch path) overrides the wall-clock stamp with a media-timeline
        timestamp; live callers omit it and keep the existing behaviour. The rate limit is
        applied on the media timeline when ts_ms is supplied."""
        clock_ms = ts_ms if ts_ms is not None else int(time.monotonic() * 1000)
        if clock_ms - self._gcv_last_ms >= self._gcv_min_interval_ms:
            self._gcv_last_ms = clock_ms
            asyncio.create_task(self._run_face_detection(frame_bytes, ts_ms))

    async def feed_frame(self, frame_bytes: bytes, ts_ms: int | None = None) -> None:
        """LLM-batch path — invoked by the LiveSessionWorkflow vision step. Buffers to
        BATCH_SIZE then runs the GPT-4o posture/gesture pass. Batch/dedup/streak state
        lives on this long-lived agent, so it survives across windows.

        `ts_ms` (feature 003 batch path) stamps emitted events with the media timeline."""
        self._frame_buf.append(frame_bytes)
        if len(self._frame_buf) >= BATCH_SIZE:
            frames = list(self._frame_buf)
            self._frame_buf.clear()
            await self._analyse(frames, ts_ms)

    async def push_frame(self, frame_bytes: bytes) -> None:
        """Back-compat: instant GCV + LLM batch in one call (used by direct callers/tests)."""
        await self.on_frame_instant(frame_bytes)
        await self.feed_frame(frame_bytes)

    # ── GCV layer ────────────────────────────────────────────────────
    async def _run_face_detection(self, frame_bytes: bytes, ts_ms: int | None = None) -> None:
        if get_settings().demo_replay or not face_detection.is_enabled():
            return
        metrics = await face_detection.detect(frame_bytes)
        if metrics is None:
            return

        if ts_ms is not None:
            self._media_clock = True
        ts = ts_ms if ts_ms is not None else self._now_ms()

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
        await self._observe(
            event_type,
            severity,
            message,
            ts,
            {
                "source": "google_vision",
                "pan_deg": metrics.pan_deg,
                "tilt_deg": metrics.tilt_deg,
                "roll_deg": metrics.roll_deg,
                "joy": metrics.joy,
                "confidence": metrics.detection_confidence,
            },
        )

    # ── LLM layer (posture / gestures only) ──────────────────────────
    async def _analyse(self, frames: list[bytes], ts_ms: int | None = None) -> None:
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

        if ts_ms is not None:
            self._media_clock = True
        ts = ts_ms if ts_ms is not None else self._now_ms()
        for raw in result.get("events", []):
            event_type = raw.get("type")
            if event_type not in _LLM_EVENT_TYPES:
                logger.warning("LLM emitted unsupported event type {} — skipped", event_type)
                continue
            await self._observe(
                event_type,
                raw.get("severity", "MEDIUM"),
                raw.get("message", ""),
                ts,
                {"source": "gpt4o_vision"},
            )

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
