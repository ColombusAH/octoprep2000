"""POST /sessions/:id/upload — multipart PPTX. Fires PPTXAgent in background."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from middleware.session_auth import require_session_owner
from orchestrator.orchestrator import Orchestrator
from workflows.pptx_prep import run_pptx_prep_workflow

router = APIRouter(prefix="/sessions", tags=["upload"])

MAX_BYTES = 50 * 1024 * 1024  # 50 MB per FR-001


@router.post("/{session_id}/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_pptx(
    session_id: uuid.UUID,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    session=Depends(require_session_owner),
):
    if not file.filename or not file.filename.lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Only .pptx accepted")

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    tmp = Path(tempfile.gettempdir()) / f"{session_id}.pptx"
    tmp.write_bytes(data)

    speech_language = session.speech_language
    deck_language = session.deck_language

    async def run_agent():
        orch = Orchestrator()
        try:
            await run_pptx_prep_workflow(
                orch,
                session_id,
                str(tmp),
                speech_language=speech_language,
                deck_language=deck_language,
            )
        finally:
            tmp.unlink(missing_ok=True)

    background.add_task(run_agent)
    return {"status": "accepted", "session_id": str(session_id)}
