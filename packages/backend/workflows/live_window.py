"""LiveWindowAggregator — turns the continuous capture stream into discrete ~2s windows.

Each arriving 2s audio chunk closes a window: buffered (deduped) frames + that chunk are
handed to one LiveSessionWorkflow run, spawned as a detached task so the WebSocket receive
loops never block on analysis. A periodic tick flushes vision-only tails when no audio is
arriving. On session end, in-flight windows are drained (so their writes land) before the
agents flush their final buffers.
"""

from __future__ import annotations

import asyncio
import uuid

from loguru import logger

from agents.audio_agent import AudioAgent
from agents.vision_agent import VisionAgent
from config import get_settings
from orchestrator.orchestrator import Orchestrator
from workflows.live_session import build_live_workflow


class LiveWindowAggregator:
    def __init__(
        self,
        session_id: uuid.UUID,
        vision: VisionAgent,
        audio: AudioAgent,
        orchestrator: Orchestrator,
    ) -> None:
        self._session_id = session_id
        self._vision = vision
        self._audio = audio
        self._orchestrator = orchestrator
        self._frames: list[bytes] = []
        self._lock = asyncio.Lock()
        self._vision_sem = asyncio.Semaphore(1)
        self._audio_sem = asyncio.Semaphore(1)
        self._workflow = build_live_workflow(
            session_id, vision, audio, orchestrator, self._vision_sem, self._audio_sem
        )
        self._tasks: set[asyncio.Task] = set()
        self._closed = False
        interval = max(1, get_settings().audio_chunk_seconds)
        self._tick_task: asyncio.Task = asyncio.create_task(self._tick_loop(interval))

    # ── ingest (called from the WS edge) ─────────────────────────────
    async def add_frame(self, frame_bytes: bytes) -> None:
        """Buffer a kept frame for the next window. GCV instant cues already fired on ingest."""
        async with self._lock:
            self._frames.append(frame_bytes)

    async def add_chunk(self, chunk: bytes) -> None:
        """A 2s audio chunk closes a window: sweep buffered frames + this chunk."""
        frames = await self._sweep_frames()
        self._spawn_window(frames, chunk)

    # ── windowing ────────────────────────────────────────────────────
    async def _sweep_frames(self) -> list[bytes]:
        async with self._lock:
            frames, self._frames = self._frames, []
        return frames

    def _spawn_window(self, frames: list[bytes], chunk: bytes | None) -> None:
        if self._closed or (not frames and chunk is None):
            return
        task = asyncio.create_task(self._run_window(frames, chunk))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run_window(self, frames: list[bytes], chunk: bytes | None) -> None:
        try:
            await self._workflow.arun(
                input=str(self._session_id),
                additional_data={"frames": frames, "chunk": chunk},
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("live window run failed: {}", exc)

    async def _tick_loop(self, interval: int) -> None:
        """Flush vision-only tails when frames accumulate without an audio chunk."""
        while not self._closed:
            await asyncio.sleep(interval)
            frames = await self._sweep_frames()
            if frames:
                self._spawn_window(frames, None)

    # ── shutdown ─────────────────────────────────────────────────────
    async def aclose(self) -> None:
        """Stop accepting input, run a final vision-only window for any tail frames, and
        drain in-flight windows so their DB writes land before the report reads."""
        self._closed = True
        self._tick_task.cancel()
        frames = await self._sweep_frames()
        if frames:
            await self._run_window(frames, None)
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)
