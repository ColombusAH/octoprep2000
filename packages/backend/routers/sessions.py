"""POST /sessions, GET /sessions/:id, POST /sessions/:id/end,
GET /sessions/:id/report, POST /sessions/:id/report/share.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from agents.schemas import CreateSessionBody, CreateSessionResponse
from core.rate_limit import SESSIONS_LIMIT, limiter
from db.repository import PostgreSQLRepository, get_repo
from middleware.session_auth import require_report_access, require_session_owner
from runtime import build_report_agent, registry

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=CreateSessionResponse, status_code=201)
@limiter.limit(SESSIONS_LIMIT)
async def create_session(
    request: Request,
    body: CreateSessionBody,
    repo: PostgreSQLRepository = Depends(get_repo),
):
    session = await repo.create_session(topic=body.topic, topic_context=body.topic_context)
    return CreateSessionResponse(session_id=session.session_id, access_token=session.access_token)


@router.get("/{session_id}")
async def get_session(
    session_id: uuid.UUID,
    session=Depends(require_session_owner),
):
    return {
        "session_id": session.session_id,
        "status": session.status,
        "topic": session.topic,
        "pptx_ready": session.pptx_ready,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
    }


@router.post("/{session_id}/end")
async def end_session(
    session_id: uuid.UUID,
    session=Depends(require_session_owner),
    repo: PostgreSQLRepository = Depends(get_repo),
):
    rt = registry.get(session_id)
    fallback = rt.orchestrator.is_fallback(session_id) if rt else False
    await registry.end(session_id)

    report_agent = await build_report_agent(repo)
    payload = await report_agent.generate(session_id, fallback_mode=fallback)

    # Persist via a fresh Orchestrator wired to this request's repo.
    from orchestrator.agno_orchestrator import AgnoOrchestrator  # local import: cycle-safe

    orch = AgnoOrchestrator(repo)
    await orch.on_report(payload)

    return {"status": "REPORT_READY", "session_id": str(session_id)}


@router.get("/{session_id}/report")
async def get_report(
    session_id: uuid.UUID,
    _=Depends(require_report_access),
    repo: PostgreSQLRepository = Depends(get_repo),
):
    report = await repo.get_report_by_session(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not ready")
    return {
        "session_id": report.session_id,
        "overall_score": float(report.overall_score or 0),
        "voice_score": float(report.voice_score or 0),
        "body_score": float(report.body_score) if report.body_score is not None else None,
        "slide_score": float(report.slide_score or 0),
        "content_score": float(report.content_score or 0),
        "insights": report.insights or [],
        "mentor_unlocked": report.mentor_unlocked,
        "generated_at": report.generated_at,
    }


@router.post("/{session_id}/report/share")
async def create_share_link(
    session_id: uuid.UUID,
    session=Depends(require_session_owner),
    repo: PostgreSQLRepository = Depends(get_repo),
):
    token = uuid.uuid4()
    await repo.set_report_share_token(session_id, token)
    return {"share_url": f"/session/{session_id}/report?share={token}"}
