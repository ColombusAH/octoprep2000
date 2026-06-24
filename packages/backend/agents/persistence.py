"""AgentPersistence — shared DB-write primitive for agents.

Constitution v2.0.0, Principle II: each agent writes only its own role-scoped rows.
This mixin gives every agent the same fresh-session-per-write pattern the Orchestrator
used (B2 fix) — no captured AsyncSession, safe across request scope.

Usage:
    class AudioAgent(AgentPersistence):
        async def push_chunk(self, ...):
            await self._with_repo(lambda r: r.insert_transcript_entry(...))
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from db.repository import PostgreSQLRepository
from db.session import get_session_maker


class AgentPersistence:
    """Mixin: fresh AsyncSession per write via get_session_maker()."""

    async def _with_repo(
        self, fn: Callable[[PostgreSQLRepository], Awaitable[Any]]
    ) -> Any:
        async with get_session_maker()() as db:
            repo = PostgreSQLRepository(db)
            return await fn(repo)
