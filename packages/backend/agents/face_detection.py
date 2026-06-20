"""Google Cloud Vision face_detection wrapper — deterministic face-metrics layer.

Calls GCV's face_detection feature through the Tikal LiteLLM gateway's
/vision/annotate route (mirrors GCV's images:annotate REST contract) — a shared
team endpoint, so no per-dev GCP service account is required.

Supplements (does NOT replace) the GPT-4o Vision agent. GCV preempts the LLM for:
  • EYE_CONTACT_LOST  — pan/tilt head angle thresholds (configurable, deg)
  • FACE_NOT_DETECTED — empty face_annotations list
  • FACE_TILTED       — roll angle threshold (sideways head tilt)
And returns joy_likelihood for the ReportAgent to use as STRENGTH signal.

Reference: https://cloud.google.com/vision/docs/reference/rest/v1/images/annotate
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx
from loguru import logger

from config import get_settings


@dataclass(frozen=True)
class FaceMetrics:
    """Output of one GCV face_detection call. None values = signal not present."""

    face_count: int
    joy: str = "UNKNOWN"
    sorrow: str = "UNKNOWN"
    anger: str = "UNKNOWN"
    surprise: str = "UNKNOWN"
    roll_deg: float | None = None
    pan_deg: float | None = None
    tilt_deg: float | None = None
    blurred: str = "UNKNOWN"
    under_exposed: str = "UNKNOWN"
    detection_confidence: float = 0.0


def is_enabled() -> bool:
    return bool(get_settings().litellm_vision_annotate_url)


async def detect(frame_bytes: bytes) -> FaceMetrics | None:
    """Run GCV face_detection on one JPEG frame via the LiteLLM gateway. None on failure / disabled."""
    if not is_enabled():
        return None
    try:
        metrics = await _call_gateway(frame_bytes)
    except Exception as exc:  # noqa: BLE001
        logger.warning("GCV face_detection call failed: {}", exc)
        return None
    logger.info(
        "GCV face_detection result: faces={} joy={} pan={} tilt={} roll={}",
        metrics.face_count,
        metrics.joy,
        metrics.pan_deg,
        metrics.tilt_deg,
        metrics.roll_deg,
    )
    return metrics


async def _call_gateway(frame_bytes: bytes) -> FaceMetrics:
    s = get_settings()
    payload = {
        "requests": [
            {
                "image": {"content": base64.b64encode(frame_bytes).decode("ascii")},
                "features": [{"type": "FACE_DETECTION", "maxResults": 10}],
            }
        ]
    }
    async with httpx.AsyncClient(timeout=s.vision_timeout_ms / 1000) as client:
        resp = await client.post(s.litellm_vision_annotate_url, json=payload)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(data["error"].get("message", "GCV gateway error"))

    response = data["responses"][0]
    if response.get("error"):
        raise RuntimeError(response["error"].get("message", "GCV error"))

    faces = response.get("faceAnnotations", [])
    if not faces:
        return FaceMetrics(face_count=0)

    # Use the highest-confidence face (largest detection score = presenter).
    face = max(faces, key=lambda f: float(f.get("detectionConfidence") or 0.0))

    return FaceMetrics(
        face_count=len(faces),
        joy=face.get("joyLikelihood", "UNKNOWN"),
        sorrow=face.get("sorrowLikelihood", "UNKNOWN"),
        anger=face.get("angerLikelihood", "UNKNOWN"),
        surprise=face.get("surpriseLikelihood", "UNKNOWN"),
        blurred=face.get("blurredLikelihood", "UNKNOWN"),
        under_exposed=face.get("underExposedLikelihood", "UNKNOWN"),
        roll_deg=float(face.get("rollAngle") or 0.0),
        pan_deg=float(face.get("panAngle") or 0.0),
        tilt_deg=float(face.get("tiltAngle") or 0.0),
        detection_confidence=float(face.get("detectionConfidence") or 0.0),
    )


# ── Heuristics derived from FaceMetrics ──────────────────────────────


def is_eye_contact_lost(m: FaceMetrics) -> bool:
    """Pan or tilt past threshold ⇒ head turned away from camera."""
    s = get_settings()
    if m.pan_deg is None or m.tilt_deg is None:
        return False
    return (
        abs(m.pan_deg) > s.face_detection_pan_threshold_deg
        or abs(m.tilt_deg) > s.face_detection_tilt_threshold_deg
    )


def is_head_tilted(m: FaceMetrics) -> bool:
    s = get_settings()
    if m.roll_deg is None:
        return False
    return abs(m.roll_deg) > s.face_detection_roll_threshold_deg


def is_smiling_strong(m: FaceMetrics) -> bool:
    return m.joy in {"LIKELY", "VERY_LIKELY"}
