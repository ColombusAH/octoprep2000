"""ffmpeg/ffprobe video decode (feature 003).

Shells out to the system ffmpeg/ffprobe to turn an uploaded rehearsal video into the
exact inputs the existing agents take:
  - frames: JPEG @ a sampled fps (each frame's media ts = index / fps)
  - audio:  raw PCM s16le, 16 kHz, mono — what AudioAgent wraps as WAV for Scribe

Raises VideoDecodeError on any failure so the caller degrades to a FAILED session
state rather than leaking raw subprocess errors (FR-011).
"""

from __future__ import annotations

import asyncio
import json
import os

from loguru import logger

MAX_FPS = 5  # constitution cap — never analyse faster than 5 fps (FR-008)


class VideoDecodeError(Exception):
    """Raised when probing or decoding the uploaded video fails."""


async def _run(cmd: list[str]) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    return proc.returncode or 0, out, err


async def probe_duration_s(path: str) -> float:
    """Return the video duration in seconds via ffprobe."""
    code, out, err = await _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            path,
        ]
    )
    if code != 0:
        raise VideoDecodeError(f"ffprobe failed: {err.decode(errors='ignore')[:300]}")
    try:
        return float(json.loads(out or b"{}")["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise VideoDecodeError(f"could not read duration: {exc}") from exc


def _clamp_fps(fps: int) -> int:
    return max(1, min(MAX_FPS, fps))


async def extract_frames(path: str, fps: int, out_dir: str) -> list[tuple[int, str]]:
    """Extract JPEG frames at `fps` (clamped ≤5). Returns ordered (index, jpg_path);
    media timestamp for index i is i / fps seconds."""
    fps = _clamp_fps(fps)
    os.makedirs(out_dir, exist_ok=True)
    pattern = os.path.join(out_dir, "frame_%06d.jpg")
    code, _out, err = await _run(
        ["ffmpeg", "-nostdin", "-i", path, "-vf", f"fps={fps}", "-q:v", "5", pattern]
    )
    if code != 0:
        raise VideoDecodeError(f"ffmpeg frame extraction failed: {err.decode(errors='ignore')[:300]}")
    files = sorted(f for f in os.listdir(out_dir) if f.startswith("frame_") and f.endswith(".jpg"))
    # ffmpeg numbers from 1; map to 0-based analysis index for media-ts math.
    frames = [(i, os.path.join(out_dir, f)) for i, f in enumerate(files)]
    logger.info("extracted {} frame(s) @ {} fps", len(frames), fps)
    return frames


async def extract_audio_pcm(path: str, out_path: str) -> str:
    """Extract the audio track as raw PCM s16le 16 kHz mono. Returns out_path.

    A video with no audio track yields an empty/absent file → caller treats as silence.
    """
    code, _out, err = await _run(
        [
            "ffmpeg",
            "-nostdin",
            "-i",
            path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "s16le",
            out_path,
        ]
    )
    if code != 0:
        raise VideoDecodeError(f"ffmpeg audio extraction failed: {err.decode(errors='ignore')[:300]}")
    return out_path
