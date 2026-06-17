"""Runtime singletons + shared dependency providers.

Holds the per-session Orchestrator + Agent registry so multiple WS handlers
(for the same session) reach the same in-memory state without race conditions.
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import Depends

from agents.audio_agent import AudioAgent
from agents.content_agent import ContentAnalysisAgent
from agents.frame_service import FrameService
from agents.report_agent import ReportAgent
from agents.vision_agent import VisionAgent
from db.repository import PostgreSQLRepository, get_repo
from orchestrator.agno_orchestrator import AgnoOrchestrator


class SessionRuntime:
    def __init__(self, orchestrator: AgnoOrchestrator) -> None:
        self.orchestrator = orchestrator
        self.vision: VisionAgent | None = None
        self.audio: AudioAgent | None = None
        self.frame_service: FrameService | None = None


class RuntimeRegistry:
    """Single in-memory map: session_id → SessionRuntime."""

    def __init__(self) -> None:
        self._runtimes: dict[uuid.UUID, SessionRuntime] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self, session_id: uuid.UUID, repo: PostgreSQLRepository
    ) -> SessionRuntime:
        async with self._lock:
            rt = self._runtimes.get(session_id)
            if rt is not None:
                return rt
            orch = AgnoOrchestrator(repo)
            await orch.start_session(session_id)
            rt = SessionRuntime(orch)
            rt.vision = VisionAgent(session_id, orch)
            rt.audio = AudioAgent(session_id, orch)
            rt.frame_service = FrameService(on_keep_frame=rt.vision.push_frame)
            self._runtimes[session_id] = rt
            return rt

    def get(self, session_id: uuid.UUID) -> SessionRuntime | None:
        return self._runtimes.get(session_id)

    async def end(self, session_id: uuid.UUID) -> None:
        rt = self._runtimes.pop(session_id, None)
        if rt is None:
            return
        await rt.orchestrator.end_session(session_id)
        if rt.audio:
            await rt.audio.aclose()


registry = RuntimeRegistry()


async def get_runtime_dep(
    session_id: uuid.UUID, repo: PostgreSQLRepository = Depends(get_repo)
) -> SessionRuntime:
    return await registry.get_or_create(session_id, repo)


async def build_report_agent(repo: PostgreSQLRepository) -> ReportAgent:
    return ReportAgent(repo, ContentAnalysisAgent(repo))
