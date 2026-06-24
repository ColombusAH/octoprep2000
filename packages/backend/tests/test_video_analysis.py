"""Tests for VideoAnalysisWorkflow — hermetic (DB + ffmpeg + agents mocked)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from media.video_decode import VideoDecodeError
from workflows import video_analysis
from workflows.video_analysis import _PCM_SAMPLE_RATE, _segment_pcm, run_video_analysis


def test_segment_pcm_slices_by_chunk_seconds():
    # 2 s of s16le 16kHz mono = 16000 * 2 bytes/s * 2 s = 64000 bytes per chunk
    per_chunk = _PCM_SAMPLE_RATE * 2 * 2
    pcm = b"\x00" * (per_chunk * 3 + 10)  # 3 full chunks + a remainder
    segs = _segment_pcm(pcm, chunk_seconds=2)
    assert len(segs) == 4
    assert all(len(s) == per_chunk for s in segs[:3])
    assert len(segs[3]) == 10


def test_segment_pcm_empty():
    assert _segment_pcm(b"", chunk_seconds=2) == []


@pytest.mark.asyncio
async def test_decode_failure_sets_failed_status():
    """SC-005 / FR-011: an undecodable video ends in FAILED, never an unhandled crash."""
    session_id = uuid.uuid4()
    statuses: list[tuple[str, str | None]] = []

    async def fake_set_status(sid, status, detail=None):
        statuses.append((status, detail))

    with patch.object(video_analysis, "Orchestrator") as Orch, patch.object(
        video_analysis, "VisionAgent"
    ), patch.object(video_analysis, "AudioAgent"), patch.object(
        video_analysis, "build_report_agent"
    ), patch.object(
        video_analysis, "_set_status", new=fake_set_status
    ), patch.object(
        video_analysis, "_clear_prior", new=AsyncMock()
    ), patch.object(
        video_analysis, "probe_duration_s", new=AsyncMock(side_effect=VideoDecodeError("bad file"))
    ):
        Orch.return_value = MagicMock(start_session=AsyncMock())
        await run_video_analysis(session_id, "/tmp/bad.mp4")

    assert ("PROCESSING", None) in statuses
    assert statuses[-1][0] == "FAILED"
    assert "bad file" in (statuses[-1][1] or "")


@pytest.mark.asyncio
async def test_replay_skips_decode_and_makes_no_live_calls():
    """FR-012 / SC-006: replay mode never invokes ffmpeg or live AI/STT."""
    session_id = uuid.uuid4()

    fake_settings = MagicMock(demo_replay=True, audio_chunk_seconds=2, video_analysis_fps=1, video_posture_stride_s=10)
    vision = MagicMock(feed_frame=AsyncMock(), on_frame_instant=AsyncMock(), aclose=AsyncMock())
    audio = MagicMock(push_chunk=AsyncMock(), aclose=AsyncMock())
    report_agent = MagicMock(generate=AsyncMock())

    with patch.object(video_analysis, "get_settings", return_value=fake_settings), patch.object(
        video_analysis, "Orchestrator"
    ) as Orch, patch.object(
        video_analysis, "VisionAgent", return_value=vision
    ), patch.object(
        video_analysis, "AudioAgent", return_value=audio
    ), patch.object(
        video_analysis, "build_report_agent", return_value=report_agent
    ), patch.object(
        video_analysis, "_set_status", new=AsyncMock()
    ), patch.object(
        video_analysis, "_clear_prior", new=AsyncMock()
    ), patch.object(
        video_analysis, "extract_frames", new=AsyncMock(side_effect=AssertionError("no decode in replay"))
    ), patch.object(
        video_analysis, "extract_audio_pcm", new=AsyncMock(side_effect=AssertionError("no decode in replay"))
    ), patch.object(
        video_analysis, "probe_duration_s", new=AsyncMock(side_effect=AssertionError("no probe in replay"))
    ):
        Orch.return_value = MagicMock(start_session=AsyncMock(), mark_report_ready=AsyncMock())
        await run_video_analysis(session_id, "/tmp/x.mp4")

    # Replay drove the agents' replay branches (no decode) and produced a report.
    audio.push_chunk.assert_awaited()
    assert vision.feed_frame.await_count == 3
    report_agent.generate.assert_awaited_once()
