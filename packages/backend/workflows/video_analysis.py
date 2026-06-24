"""VideoAnalysisWorkflow — batch analysis of an uploaded rehearsal video (feature 003).

Off the real-time path: decode the video with ffmpeg into frames + PCM, drive the SAME
VisionAgent / AudioAgent the live path uses (so they write the same transcript_entries /
video_events / audio_warnings rows), then hand off to the existing report path. Timestamps
come from the video's media timeline. agno glue only: telemetry=False, db=None; agents own
all writes (Principle II). Every run reaches a terminal session status (REPORT_READY or
FAILED) and cleans its temp workspace.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid

from agno.workflow import Step, Workflow
from agno.workflow.types import StepInput, StepOutput
from loguru import logger

from agents.audio_agent import AudioAgent
from agents.frame_service import FrameService
from agents.vision_agent import VisionAgent
from config import get_settings
from db.repository import PostgreSQLRepository
from db.session import get_session_maker
from media.video_decode import (
    VideoDecodeError,
    extract_audio_pcm,
    extract_frames,
    probe_duration_s,
)
from orchestrator.orchestrator import Orchestrator
from runtime import build_report_agent

_PCM_BYTES_PER_SAMPLE = 2  # s16le
_PCM_SAMPLE_RATE = 16000
_PCM_CHANNELS = 1


async def _set_status(session_id: uuid.UUID, status: str, detail: str | None = None) -> None:
    async with get_session_maker()() as db:
        await PostgreSQLRepository(db).set_session_status(session_id, status, detail)


async def _clear_prior(session_id: uuid.UUID) -> None:
    async with get_session_maker()() as db:
        await PostgreSQLRepository(db).clear_session_derived_rows(session_id)


def _segment_pcm(pcm: bytes, chunk_seconds: int) -> list[bytes]:
    step = _PCM_SAMPLE_RATE * _PCM_CHANNELS * _PCM_BYTES_PER_SAMPLE * chunk_seconds
    if step <= 0:
        return [pcm] if pcm else []
    return [pcm[i : i + step] for i in range(0, len(pcm), step)] or []


async def _analyse_audio(audio: AudioAgent, pcm_path: str, chunk_seconds: int) -> None:
    try:
        with open(pcm_path, "rb") as fh:
            pcm = fh.read()
    except OSError:
        pcm = b""
    for seg in _segment_pcm(pcm, chunk_seconds):
        if seg:
            await audio.push_chunk(seg)


async def _analyse_vision(
    vision: VisionAgent, frames: list[tuple[int, str]], fps: int, stride_s: int
) -> None:
    cur: dict = {"ts": 0, "feed": False}

    async def on_keep(frame_bytes: bytes) -> None:
        await vision.on_frame_instant(frame_bytes, cur["ts"])
        if cur["feed"]:
            await vision.feed_frame(frame_bytes, cur["ts"])

    fs = FrameService(on_keep_frame=on_keep)
    posture_next_ms = 0
    for idx, path in frames:
        cur["ts"] = int(idx / max(1, fps) * 1000)
        cur["feed"] = cur["ts"] >= posture_next_ms
        try:
            with open(path, "rb") as fh:
                frame_bytes = fh.read()
        except OSError:
            continue
        kept = await fs.ingest(frame_bytes)
        if kept and cur["feed"]:
            posture_next_ms = cur["ts"] + stride_s * 1000


async def run_video_analysis(session_id: uuid.UUID, video_path: str) -> None:
    settings = get_settings()
    orch = Orchestrator()
    await orch.start_session(session_id)
    vision = VisionAgent(session_id, orch)
    audio = AudioAgent(session_id, orch)
    ctx: dict = {}
    workdir = tempfile.mkdtemp(prefix=f"video-{session_id}-")

    # agno Workflow retries a failing step and continues to the next regardless, so each
    # step handles its own errors and sets a terminal FAILED status + a short-circuit flag.
    ctx["failed"] = False

    async def _fail(reason_log: str, detail: str, exc: Exception) -> None:
        logger.warning("video analysis {} for {}: {}", reason_log, session_id, exc)
        ctx["failed"] = True
        await _set_status(session_id, "FAILED", detail)

    async def extract_step(_si: StepInput) -> StepOutput:
        try:
            await _set_status(session_id, "PROCESSING")
            await _clear_prior(session_id)
            if settings.demo_replay:
                ctx["frames"], ctx["pcm_path"] = [], ""
                return StepOutput(content="replay — skipping decode")
            await probe_duration_s(video_path)  # validated at upload; cheap re-probe insurance
            ctx["frames"] = await extract_frames(video_path, settings.video_analysis_fps, workdir)
            ctx["pcm_path"] = await extract_audio_pcm(video_path, os.path.join(workdir, "audio.pcm"))
            return StepOutput(content=f"extracted {len(ctx['frames'])} frame(s)")
        except VideoDecodeError as exc:
            await _fail("decode failure", f"Could not process video: {exc}", exc)
            return StepOutput(content="extract failed")

    async def analyse_step(_si: StepInput) -> StepOutput:
        if ctx["failed"]:
            return StepOutput(content="skipped (failed)")
        try:
            if settings.demo_replay:
                # Drive the agents' replay branches to write fixture rows (no live AI/STT).
                await audio.push_chunk(b"")
                for _ in range(3):
                    await vision.feed_frame(b"", 0)
            else:
                chunk_seconds = max(1, settings.audio_chunk_seconds)
                await _analyse_audio(audio, ctx["pcm_path"], chunk_seconds)
                await _analyse_vision(
                    vision,
                    ctx["frames"],
                    settings.video_analysis_fps,
                    settings.video_posture_stride_s,
                )
            await vision.aclose()
            await audio.aclose()
            return StepOutput(content="analysis complete")
        except Exception as exc:  # noqa: BLE001
            await _fail("analysis error", "Video analysis failed — please try again.", exc)
            return StepOutput(content="analyse failed")

    async def report_step(_si: StepInput) -> StepOutput:
        if ctx["failed"]:
            return StepOutput(content="skipped (failed)")
        try:
            await build_report_agent(orch).generate(session_id)
            await orch.mark_report_ready(session_id)
            return StepOutput(content="report ready")
        except Exception as exc:  # noqa: BLE001
            await _fail("report error", "Video analysis failed — please try again.", exc)
            return StepOutput(content="report failed")

    workflow = Workflow(
        name="video-analysis",
        telemetry=False,
        db=None,
        steps=[
            Step(name="extract", executor=extract_step),
            Step(name="analyse", executor=analyse_step),
            Step(name="report", executor=report_step),
        ],
    )

    try:
        await workflow.arun(input=str(session_id))
    except Exception as exc:  # noqa: BLE001 — last-resort guard; steps already self-handle
        await _fail("unexpected error", "Video analysis failed — please try again.", exc)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
