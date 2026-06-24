"""POST /sessions/:id/upload-video — multipart video. Validates then runs batch analysis.

Alternative to a live rehearsal (feature 003): the uploaded video is analysed in the
background by VideoAnalysisWorkflow, producing the same report. Validation (format →
size → duration) happens up front so bad inputs fail fast before any heavy work.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from config import get_settings
from media.video_decode import VideoDecodeError, probe_duration_s
from middleware.session_auth import require_session_owner
from workflows.video_analysis import run_video_analysis

router = APIRouter(prefix="/sessions", tags=["upload-video"])

ALLOWED_EXTENSIONS = (".mp4", ".mov", ".m4v", ".webm")


@router.post("/{session_id}/upload-video", status_code=status.HTTP_202_ACCEPTED)
async def upload_video(
    session_id: uuid.UUID,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    _=Depends(require_session_owner),
):
    settings = get_settings()

    name = (file.filename or "").lower()
    if not name.endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Only video files accepted: mp4, mov, m4v, webm",
        )

    data = await file.read()
    if len(data) > settings.video_max_bytes:
        mb = settings.video_max_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"File too large (max {mb}MB)")

    tmp = Path(tempfile.gettempdir()) / f"{session_id}-upload{Path(name).suffix}"
    tmp.write_bytes(data)

    try:
        duration = await probe_duration_s(str(tmp))
    except VideoDecodeError:
        tmp.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Could not read video — is it a valid file?")

    if duration > settings.video_max_duration_s:
        tmp.unlink(missing_ok=True)
        mins = settings.video_max_duration_s // 60
        raise HTTPException(status_code=400, detail=f"Video too long (max {mins} minutes)")

    async def run() -> None:
        try:
            await run_video_analysis(session_id, str(tmp))
        finally:
            tmp.unlink(missing_ok=True)

    background.add_task(run)
    return {"status": "accepted", "session_id": str(session_id)}
