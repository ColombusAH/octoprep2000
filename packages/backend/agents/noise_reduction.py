"""Spectral noise gating for raw PCM 16-bit mono chunks.

Applied per 2s chunk in AudioAgent.push_chunk before ElevenLabs STT.
Never raises — exceptions fall back to the raw input.
"""

from __future__ import annotations

import time

import numpy as np
import noisereduce as nr
from loguru import logger

from config import get_settings


def apply_noise_reduction(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    if not get_settings().noise_reduction_enabled:
        return pcm_bytes

    if not pcm_bytes:
        return pcm_bytes

    t0 = time.monotonic()
    try:
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        reduced = nr.reduce_noise(y=audio, sr=sample_rate, stationary=False, prop_decrease=0.75)
        result = np.nan_to_num(reduced, nan=0.0).clip(-1.0, 1.0)
        out = (result * 32768.0).astype(np.int16).tobytes()
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.debug("Noise reduction: {}ms for {} bytes", round(elapsed_ms, 1), len(pcm_bytes))
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("Noise reduction failed ({}), passing raw audio", exc)
        return pcm_bytes
