"""LiveWindowAggregator + LiveSessionWorkflow wiring.

Proves the per-window agno Workflow delegates into the long-lived agents, that audio-only
fallback skips the vision step, and that aclose() drains in-flight windows. No network/DB:
the vision/audio agents are mocked, so only the workflow glue is under test.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from orchestrator.orchestrator import Orchestrator
from workflows.live_window import LiveWindowAggregator


def _agg(orch: Orchestrator):
    sid = uuid.uuid4()
    vision = AsyncMock()
    audio = AsyncMock()
    agg = LiveWindowAggregator(sid, vision, audio, orch)
    return sid, vision, audio, agg


@pytest.mark.asyncio
async def test_window_delegates_frames_and_chunk_to_agents():
    orch = Orchestrator()
    sid, vision, audio, agg = _agg(orch)
    await orch.start_session(sid)

    await agg.add_frame(b"f1")
    await agg.add_frame(b"f2")
    await agg.add_chunk(b"chunk")  # closes the window
    await agg.aclose()

    # vision LLM batch fed both buffered frames; audio processed the chunk.
    assert vision.feed_frame.await_count == 2
    audio.push_chunk.assert_awaited_once_with(b"chunk")
    # instant GCV path is NOT driven from the window (it fires on ingest).
    vision.on_frame_instant.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_skips_vision_but_keeps_audio():
    orch = Orchestrator()
    sid, vision, audio, agg = _agg(orch)
    await orch.start_session(sid)
    await orch.activate_fallback(sid)  # audio-only mode

    await agg.add_frame(b"f1")
    await agg.add_chunk(b"chunk")
    await agg.aclose()

    vision.feed_frame.assert_not_called()
    audio.push_chunk.assert_awaited_once_with(b"chunk")


@pytest.mark.asyncio
async def test_aclose_flushes_vision_only_tail():
    orch = Orchestrator()
    sid, vision, audio, agg = _agg(orch)
    await orch.start_session(sid)

    await agg.add_frame(b"tail")  # no audio chunk arrives
    await agg.aclose()            # final vision-only window must still run

    vision.feed_frame.assert_awaited_once_with(b"tail")
    audio.push_chunk.assert_not_called()
