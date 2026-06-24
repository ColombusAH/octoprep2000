"""Runtime singletons + shared dependency providers.

Holds the per-session Orchestrator + Agent registry so multiple WS handlers
(for the same session) reach the same in-memory state without race conditions.

Orchestrator owns no DB handle (B2 fix) — opens fresh AsyncSession per write
via get_session_maker(). Safe across request boundaries.
"""

from __future__ import annotations

import asyncio
import uuid

from agents.audio_agent import AudioAgent
from agents.content_agent import ContentAnalysisAgent
from agents.frame_service import FrameService
from agents.pptx_agent import PPTXAgent
from agents.report_agent import ReportAgent
from agents.vision_agent import VisionAgent
from orchestrator.orchestrator import Orchestrator
from workflows.live_window import LiveWindowAggregator


class SessionRuntime:
    def __init__(self, session_id: uuid.UUID, orchestrator: Orchestrator) -> None:
        self.session_id = session_id
        self.orchestrator = orchestrator
        self.pptx: PPTXAgent | None = None
        self.vision: VisionAgent | None = None
        self.audio: AudioAgent | None = None
        self.frame_service: FrameService | None = None
        self.aggregator: LiveWindowAggregator | None = None


class RuntimeRegistry:
    """Single in-memory map: session_id → SessionRuntime."""

    def __init__(self) -> None:
        self._runtimes: dict[uuid.UUID, SessionRuntime] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, session_id: uuid.UUID) -> SessionRuntime:
        async with self._lock:
            rt = self._runtimes.get(session_id)
            if rt is not None:
                return rt
            orch = Orchestrator()
            await orch.start_session(session_id)
            rt = SessionRuntime(session_id, orch)
            rt.pptx = PPTXAgent(orch, session_id=session_id)
            rt.vision = VisionAgent(session_id, orch)
            rt.audio = AudioAgent(
                session_id,
                orch,
                slide_state_provider=rt.pptx.get_slide_state,
            )
            rt.aggregator = LiveWindowAggregator(session_id, rt.vision, rt.audio, orch)

            async def _on_keep_frame(frame: bytes, rt: SessionRuntime = rt) -> None:
                # Instant GCV cues fire here (off the agno window); the frame is then
                # buffered for the LiveSessionWorkflow's per-window LLM batch.
                assert rt.vision is not None and rt.aggregator is not None
                await rt.vision.on_frame_instant(frame)
                await rt.aggregator.add_frame(frame)

            rt.frame_service = FrameService(on_keep_frame=_on_keep_frame)
            self._runtimes[session_id] = rt
            return rt

    def get(self, session_id: uuid.UUID) -> SessionRuntime | None:
        return self._runtimes.get(session_id)

    async def end(self, session_id: uuid.UUID) -> None:
        rt = self._runtimes.pop(session_id, None)
        if rt is None:
            return
        await rt.orchestrator.end_session(session_id)
        # Drain any in-flight live windows first so their writes land, THEN flush the
        # VisionAgent's final batch so video_events are durable before the ReportAgent
        # reads them (Principle II — durability before report assembly).
        if rt.aggregator:
            await rt.aggregator.aclose()
        if rt.vision:
            await rt.vision.aclose()
        if rt.audio:
            await rt.audio.aclose()


registry = RuntimeRegistry()


def build_report_agent(orchestrator: Orchestrator | None = None) -> ReportAgent:
    return ReportAgent(ContentAnalysisAgent(), orchestrator=orchestrator)
