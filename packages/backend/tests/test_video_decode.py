"""Tests for media.video_decode — ffmpeg/ffprobe stubbed (no real decode, no network)."""

from __future__ import annotations

import os

import pytest

from media import video_decode
from media.video_decode import (
    MAX_FPS,
    VideoDecodeError,
    _clamp_fps,
    extract_frames,
    probe_duration_s,
)


def test_clamp_fps_caps_at_five():
    assert _clamp_fps(1) == 1
    assert _clamp_fps(5) == 5
    assert _clamp_fps(30) == MAX_FPS  # FR-008 — never exceed 5 fps
    assert _clamp_fps(0) == 1


@pytest.mark.asyncio
async def test_probe_duration_parses(monkeypatch):
    async def fake_run(cmd):
        return 0, b'{"format": {"duration": "123.45"}}', b""

    monkeypatch.setattr(video_decode, "_run", fake_run)
    assert await probe_duration_s("x.mp4") == pytest.approx(123.45)


@pytest.mark.asyncio
async def test_probe_raises_on_ffprobe_error(monkeypatch):
    async def fake_run(cmd):
        return 1, b"", b"boom"

    monkeypatch.setattr(video_decode, "_run", fake_run)
    with pytest.raises(VideoDecodeError):
        await probe_duration_s("x.mp4")


@pytest.mark.asyncio
async def test_extract_frames_clamps_fps_and_orders(monkeypatch, tmp_path):
    captured: dict = {}

    async def fake_run(cmd):
        captured["cmd"] = cmd
        # Simulate ffmpeg writing frames to the out_dir.
        for i in (1, 2, 3):
            (tmp_path / f"frame_{i:06d}.jpg").write_bytes(b"jpg")
        return 0, b"", b""

    monkeypatch.setattr(video_decode, "_run", fake_run)
    frames = await extract_frames("x.mp4", fps=30, out_dir=str(tmp_path))

    assert [idx for idx, _ in frames] == [0, 1, 2]  # 0-based for media-ts math
    assert all(os.path.exists(p) for _, p in frames)
    assert "fps=5" in " ".join(captured["cmd"])  # clamped from 30 → 5


@pytest.mark.asyncio
async def test_extract_frames_raises_on_ffmpeg_error(monkeypatch, tmp_path):
    async def fake_run(cmd):
        return 1, b"", b"decode error"

    monkeypatch.setattr(video_decode, "_run", fake_run)
    with pytest.raises(VideoDecodeError):
        await extract_frames("x.mp4", fps=1, out_dir=str(tmp_path))
