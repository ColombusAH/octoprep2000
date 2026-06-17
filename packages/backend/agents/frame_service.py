"""Algorithmic frame delta — drops redundant frames before VisionAgent.

Per §5b + open-decision-3: imagehash dhash, Hamming threshold 8 (tunable).
Non-agent. No LLM calls. No DB access. Pure utility.
"""

from __future__ import annotations

import io
import logging
from collections.abc import Awaitable, Callable

import imagehash
from PIL import Image

from config import get_settings

logger = logging.getLogger(__name__)


class FrameService:
    def __init__(self, on_keep_frame: Callable[[bytes], Awaitable[None]]) -> None:
        self._on_keep_frame = on_keep_frame
        self._prev_hash: imagehash.ImageHash | None = None
        self._threshold = get_settings().frame_dedup_hamming_threshold

    async def ingest(self, frame_bytes: bytes) -> bool:
        """Returns True if frame was kept (delta > threshold), False if dropped."""
        try:
            img = Image.open(io.BytesIO(frame_bytes))
            h = imagehash.dhash(img)
        except Exception as exc:  # noqa: BLE001
            logger.warning("frame decode failed: %s", exc)
            return False

        if self._prev_hash is None:
            self._prev_hash = h
            await self._on_keep_frame(frame_bytes)
            return True

        distance = h - self._prev_hash
        if distance > self._threshold:
            self._prev_hash = h
            await self._on_keep_frame(frame_bytes)
            return True
        return False

    def reset(self) -> None:
        self._prev_hash = None
