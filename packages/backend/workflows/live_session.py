"""LiveSessionWorkflow — one agno Workflow run per ~2s capture window.

A single agno Parallel group ("LiveAnalysisTeam") runs the two modalities concurrently.
Each step delegates into the long-lived, stateful VisionAgent / AudioAgent held on the
SessionRuntime — their dedup / timeout-streak / WPM-window / batch-buffer state survives
across windows precisely because the agents are NOT re-created per run.

Parallel (not a coordinator Team) is deliberate: the two modalities are fixed and
independent, and audio is fully deterministic (STT + regex + WPM math, no LLM), so a
routing/synthesizing leader would be pure latency. Instant GCV face cues run on frame
ingest, OUTSIDE this workflow. agno glue only: telemetry=False, db=None; agents own all
writes (Principle II); in-process (Principle V).
"""

from __future__ import annotations

import asyncio
import uuid

from agno.workflow import Parallel, Step, Workflow
from agno.workflow.types import StepInput, StepOutput

from agents.audio_agent import AudioAgent
from agents.vision_agent import VisionAgent
from orchestrator.orchestrator import Orchestrator


def build_live_workflow(
    session_id: uuid.UUID,
    vision: VisionAgent,
    audio: AudioAgent,
    orchestrator: Orchestrator,
    vision_sem: asyncio.Semaphore,
    audio_sem: asyncio.Semaphore,
) -> Workflow:
    """Build the per-session workflow ONCE; the aggregator runs it once per window.

    The per-modality semaphores keep one window in flight per modality, preserving
    ordering (chunk counter / WPM window) and the agents' internal state.
    """

    async def vision_step(si: StepInput) -> StepOutput:
        if orchestrator.is_fallback(session_id):
            return StepOutput(content="vision skipped (audio-only fallback)")
        frames = (si.additional_data or {}).get("frames") or []
        async with vision_sem:
            for frame in frames:
                await vision.feed_frame(frame)
        return StepOutput(content=f"vision processed {len(frames)} frame(s)")

    async def audio_step(si: StepInput) -> StepOutput:
        chunk = (si.additional_data or {}).get("chunk")
        if not chunk:
            return StepOutput(content="audio idle (no chunk this window)")
        async with audio_sem:
            await audio.push_chunk(chunk)
        return StepOutput(content="audio processed chunk")

    return Workflow(
        name="live-session",
        telemetry=False,
        db=None,
        steps=[
            Parallel(
                Step(name="vision", executor=vision_step),
                Step(name="audio", executor=audio_step),
                name="LiveAnalysisTeam",
            ),
        ],
    )
