"""Google Cloud Vision face_detection wrapper — deterministic face-metrics layer.

Supplements (does NOT replace) the GPT-4o Vision agent. GCV preempts the LLM for:
  • EYE_CONTACT_LOST  — pan/tilt head angle thresholds (configurable, deg)
  • FACE_NOT_DETECTED — empty face_annotations list
  • FACE_TILTED       — roll angle threshold (sideways head tilt)
And returns joy_likelihood for the ReportAgent to use as STRENGTH signal.

GCV SDK is sync; we call it via asyncio.to_thread to keep the FastAPI event loop free.

Reference: https://docs.cloud.google.com/vision/docs/detecting-faces
Auth: GOOGLE_APPLICATION_CREDENTIALS env var → path to service-account JSON.
"""

from __future__ import annotations

import asyncio
from loguru import logger
from dataclasses import dataclass
from functools import lru_cache

from config import get_settings


# Mirrors google.cloud.vision Likelihood enum ordering (UNKNOWN=0 … VERY_LIKELY=5)
LIKELIHOOD_NAME = (
    "UNKNOWN",
    "VERY_UNLIKELY",
    "UNLIKELY",
    "POSSIBLE",
    "LIKELY",
    "VERY_LIKELY",
)


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


@lru_cache(maxsize=1)
def _client():
    """Lazy ImageAnnotatorClient. Returns None if SDK missing or credentials unset."""
    s = get_settings()
    if not s.google_application_credentials:
        logger.info("GCV face detection disabled (GOOGLE_APPLICATION_CREDENTIALS unset).")
        return None
    try:
        from google.cloud import vision  # type: ignore
    except ImportError:
        logger.warning("google-cloud-vision not installed; face detection disabled.")
        return None
    try:
        return vision.ImageAnnotatorClient()
    except Exception as exc:  # noqa: BLE001
        logger.warning("GCV client init failed: {} — face detection disabled.", exc)
        return None


def is_enabled() -> bool:
    return _client() is not None


async def detect(frame_bytes: bytes) -> FaceMetrics | None:
    """Run GCV face_detection on one JPEG frame. None on failure / disabled."""
    client = _client()
    if client is None:
        return None
    try:
        return await asyncio.to_thread(_blocking_call, client, frame_bytes)
    except Exception as exc:  # noqa: BLE001
        logger.warning("GCV face_detection call failed: {}", exc)
        return None


def _blocking_call(client, frame_bytes: bytes) -> FaceMetrics:
    """Synchronous GCV call — must run in to_thread."""
    from google.cloud import vision  # type: ignore

    image = vision.Image(content=frame_bytes)
    response = client.face_detection(image=image)
    if response.error.message:
        raise RuntimeError(response.error.message)

    faces = response.face_annotations
    if not faces:
        return FaceMetrics(face_count=0)

    # Use the highest-confidence face (largest detection score = presenter).
    face = max(faces, key=lambda f: float(f.detection_confidence or 0.0))

    return FaceMetrics(
        face_count=len(faces),
        joy=LIKELIHOOD_NAME[face.joy_likelihood],
        sorrow=LIKELIHOOD_NAME[face.sorrow_likelihood],
        anger=LIKELIHOOD_NAME[face.anger_likelihood],
        surprise=LIKELIHOOD_NAME[face.surprise_likelihood],
        blurred=LIKELIHOOD_NAME[face.blurred_likelihood],
        under_exposed=LIKELIHOOD_NAME[face.under_exposed_likelihood],
        roll_deg=float(face.roll_angle),
        pan_deg=float(face.pan_angle),
        tilt_deg=float(face.tilt_angle),
        detection_confidence=float(face.detection_confidence or 0.0),
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
