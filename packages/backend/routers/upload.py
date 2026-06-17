"""POST /sessions/:id/upload — multipart PPTX. Fires PPTXAgent in background."""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from agents.pptx_agent import PPTXAgent
from db.repository import PostgreSQLRepository, get_repo
from middleware.session_auth import require_session_owner
from orchestrator.agno_orchestrator import AgnoOrchestrator

router = APIRouter(prefix="/sessions", tags=["upload"])

MAX_BYTES = 50 * 1024 * 1024  # 50 MB per FR-001


@router.post("/{session_id}/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_pptx(
    session_id: uuid.UUID,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    _=Depends(require_session_owner),
    repo: PostgreSQLRepository = Depends(get_repo),
):
    if not file.filename or not file.filename.lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Only .pptx accepted")

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    tmp = Path(tempfile.gettempdir()) / f"{session_id}.pptx"
    tmp.write_bytes(data)

    async def run_agent():
        orch = AgnoOrchestrator(repo)
        agent = PPTXAgent(orch)
        try:
            await agent.analyse(session_id, str(tmp))
        finally:
            tmp.unlink(missing_ok=True)

    background.add_task(asyncio.create_task, run_agent())
    return {"status": "accepted", "session_id": str(session_id)}
