"""Coordinator. Owns session lifecycle, cross-agent coordination, and report assembly.

Constitution v2.0.0, Principle II: agents write their OWN role-scoped rows (see
agents/persistence.py) and emit a CompletionSignal here via `notify_complete`. The
Orchestrator no longer relays raw payloads as a persistence pipe — it reads the agreed
tables (via ReportAgent) to assemble the report.

Lifecycle note (B2 fix): Orchestrator holds no AsyncSession. The few writes it still owns
(session status transitions) open a fresh session via `get_session_maker()`.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from agents.schemas import CompletionKind
from core.feedback_broadcaster import broadcaster
from db.repository import PostgreSQLRepository
from db.session import get_session_maker


class Orchestrator:
    def __init__(self) -> None:
        self._tasks: dict[uuid.UUID, dict[str, asyncio.Task]] = {}
        self._fallback_active: set[uuid.UUID] = set()
        self._completion: dict[uuid.UUID, set[CompletionKind]] = {}

    # ── DB write helper: fresh session per call ──────────────────────
    async def _with_repo(self, fn: Callable[[PostgreSQLRepository], Awaitable[Any]]) -> Any:
        async with get_session_maker()() as db:
            repo = PostgreSQLRepository(db)
            return await fn(repo)

    # ── Session lifecycle ────────────────────────────────────────────
    async def start_session(self, session_id: uuid.UUID) -> None:
        self._tasks.setdefault(session_id, {})
        self._completion.setdefault(session_id, set())
        logger.info("Orchestrator: session {} started", session_id)

    async def end_session(self, session_id: uuid.UUID) -> None:
        for name, task in self._tasks.get(session_id, {}).items():
            task.cancel()
            logger.debug("cancelled task {} for {}", name, session_id)
        await self._with_repo(lambda r: r.set_session_status(session_id, "ENDED"))
        logger.info("Orchestrator: session {} ended", session_id)

    async def mark_report_ready(self, session_id: uuid.UUID) -> None:
        await self._with_repo(lambda r: r.set_session_status(session_id, "REPORT_READY"))
        await broadcaster.publish(
            session_id, {"type": "REPORT_READY", "session_id": str(session_id)}
        )

    # ── Completion signal (agent → Orchestrator) ─────────────────────
    async def notify_complete(
        self, session_id: uuid.UUID, kind: CompletionKind, meta: dict | None = None
    ) -> None:
        """Record that an agent finished a unit of work AFTER its write committed.

        Advisory coordination only — the data already lives in the agreed tables.
        """
        self._completion.setdefault(session_id, set()).add(kind)
        logger.debug("completion: {} {} meta={}", session_id, kind, meta)

    def completed(self, session_id: uuid.UUID) -> set[CompletionKind]:
        return self._completion.get(session_id, set())

    # ── Audio-only fallback (§4c) ────────────────────────────────────
    async def activate_fallback(self, session_id: uuid.UUID) -> None:
        if session_id in self._fallback_active:
            return
        self._fallback_active.add(session_id)
        video_task = self._tasks.get(session_id, {}).pop("video", None)
        if video_task:
            video_task.cancel()
        await broadcaster.publish(
            session_id,
            {
                "type": "FALLBACK_ACTIVATED",
                "message": "Video analysis unavailable — continuing with audio coaching",
            },
        )

    def is_fallback(self, session_id: uuid.UUID) -> bool:
        return session_id in self._fallback_active

    def register_task(self, session_id: uuid.UUID, name: str, task: asyncio.Task) -> None:
        self._tasks.setdefault(session_id, {})[name] = task
