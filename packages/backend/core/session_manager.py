"""Session lifecycle state machine: ACTIVE → ENDED → REPORT_READY."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from db.models import Session as SessionModel
from db.repository import PostgreSQLRepository


class SessionManager:
    VALID_TRANSITIONS = {
        "ACTIVE": {"ENDED"},
        "ENDED": {"REPORT_READY"},
        "REPORT_READY": set(),
    }

    def __init__(self, repo: PostgreSQLRepository) -> None:
        self.repo = repo

    async def create(self, topic: str, topic_context: str | None = None) -> SessionModel:
        return await self.repo.create_session(topic=topic, topic_context=topic_context)

    async def transition(self, session_id: uuid.UUID, target: str) -> SessionModel:
        session = await self.repo.get_session(session_id)
        if not session:
            raise LookupError(f"session {session_id} not found")
        if target not in self.VALID_TRANSITIONS.get(session.status, set()):
            raise ValueError(
                f"illegal transition {session.status} → {target} (session={session_id})"
            )
        session.status = target
        if target == "ENDED":
            session.ended_at = datetime.now(tz=timezone.utc)
        await self.repo.db.commit()
        await self.repo.db.refresh(session)
        return session
