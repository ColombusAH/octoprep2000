"""Capability-token auth per TECH-ARCH §5.

- HTTP routes: `Authorization: Bearer <access_token>` → `require_session_owner`
- Report: access_token OR share_token (query param) → `require_report_access`
- WebSocket: `?session_id=X&token=Y` validated on handshake → `validate_ws_token`
"""

from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException, status

from db.repository import PostgreSQLRepository, get_repo


async def require_session_owner(
    session_id: uuid.UUID,
    authorization: str = Header(..., alias="Authorization"),
    repo: PostgreSQLRepository = Depends(get_repo),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer required")

    access_token = authorization.removeprefix("Bearer ").strip()
    session = await repo.get_session(session_id)

    if not session or str(session.access_token) != access_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired session token"
        )
    return session


async def require_report_access(
    session_id: uuid.UUID,
    authorization: str = Header(default="", alias="Authorization"),
    share: str | None = None,
    repo: PostgreSQLRepository = Depends(get_repo),
):
    if authorization.startswith("Bearer "):
        access_token = authorization.removeprefix("Bearer ").strip()
        session = await repo.get_session(session_id)
        if session and str(session.access_token) == access_token:
            return session

    if share:
        report = await repo.get_report_by_session(session_id)
        if report and report.share_token and str(report.share_token) == share:
            return report

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


async def validate_ws_token(
    session_id: uuid.UUID, token: str, repo: PostgreSQLRepository
) -> bool:
    session = await repo.get_session(session_id)
    return session is not None and str(session.access_token) == token
