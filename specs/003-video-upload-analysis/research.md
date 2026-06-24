# Phase 0 Research: Uploaded Video Batch Analysis

**Feature**: `003-video-upload-analysis` | **Date**: 2026-06-24

All Technical Context unknowns are resolved below. No NEEDS CLARIFICATION remain.

---

## Decision 1 — Decode with system `ffmpeg`/`ffprobe` via subprocess

**Decision**: Shell out to the system `ffmpeg` (decode) and `ffprobe` (validate/probe). Two extractions:
- **Frames**: `ffmpeg -i in -vf fps=<rate> -q:v 5 frame_%06d.jpg` at the configured analysis fps (default 1, hard cap 5). Each frame's media timestamp = `(index - 1) / rate * 1000` ms.
- **Audio**: `ffmpeg -i in -vn -ac 1 -ar 16000 -f s16le out.pcm` → raw PCM 16-bit mono 16 kHz — **exactly** what `AudioAgent` already wraps as WAV and sends to Scribe.
- **Probe**: `ffprobe -v error -show_entries format=duration -of json in` for the duration gate (FR-003).

**Rationale**: ffmpeg handles the broad consumer container/codec matrix the user named (MP4/H.264, MOV/QuickTime, WebM) and emits the agents' native inputs directly (JPEG bytes; PCM 16 kHz mono). No format-conversion glue, no Python compiled wheel.

**Alternatives considered**:
- *opencv / imageio*: frames only — no audio track extraction; narrower codec support. Rejected.
- *PyAV*: a compiled ffmpeg binding (build burden) that still wraps ffmpeg. Rejected for subprocess simplicity.

**Constraint**: ffmpeg/ffprobe must be on the host/image. Local dev: usually present (or `brew install ffmpeg`). Railway/Docker: add `ffmpeg` to the build (apt). Captured as an infra task; the feature is inert without it, so the endpoint surfaces a clear `FAILED` reason if the binary is missing.

---

## Decision 2 — Media-timeline timestamps via an additive VisionAgent override

**Decision**: Audio already timestamps by chunk index (`chunk_count * audio_chunk_seconds * 1000`), which is media-relative when chunks are fed in order — **no change**. VisionAgent currently derives `ts` from `_now_ms()` (monotonic − session start = wall-clock), which is wrong for batch. Add an optional `ts_ms: int | None = None` parameter to `on_frame_instant`, `feed_frame`, and `_analyse`; when provided, events use it instead of `_now_ms()`. Live callers pass nothing → behavior unchanged.

**Rationale**: Minimal, additive, satisfies FR-007 / SC-003 (insight timestamps map to the video position). The batch driver knows each frame's media time from the extraction index and threads it through.

**Alternatives considered**:
- *Rebase `_session_started_ms`*: fragile (assumes uniform processing cadence); rejected.
- *Post-process timestamps after the fact*: would require remembering frame→event association outside the agent; rejected.

---

## Decision 3 — `VideoAnalysisWorkflow` orchestrates extract → analyse → report

**Decision**: A new agno `Workflow` (pure glue: `telemetry=False, db=None`) run as a FastAPI background task:
1. **extract** — probe + ffmpeg frames/audio to a temp workspace.
2. **analyse** — a `Parallel`-style pair (mirroring `LiveAnalysisTeam`): an audio task feeds 2-s PCM segments to `AudioAgent.push_chunk` in order; a vision task feeds extracted frames (after `FrameService` dedup) to `on_frame_instant(frame, ts) + feed_frame(frame, ts)` in order. Within each modality, order is preserved (agent internal state); across modalities they run concurrently.
3. **flush** — `vision.aclose()` / `audio.aclose()` so all rows are durable.
4. **report handoff** — call the existing `build_report_agent(orch).generate(session_id)` then `orch.mark_report_ready(session_id)` — the same path `POST /sessions/{id}/end` uses.

Fresh `Orchestrator` + `VisionAgent` + `AudioAgent` + `FrameService` are constructed for the job (no WS, no `LiveWindowAggregator`).

**Rationale**: Reuses the entire write + report machinery; the only new orchestration is feeding agents from a file instead of a socket. Matches the constitution's sanctioned Workflow substrate.

**Resilience (FR-011)**: extraction/STT/vision failures are caught; the job still flushes whatever rows succeeded and generates a partial report when possible. An unrecoverable failure (e.g. undecodable file) sets `status=FAILED` with a reason and never raises out of the background task. Every job ends in a terminal state (`REPORT_READY` or `FAILED`) — SC-005.

---

## Decision 4 — Bounding vision cost for long videos

**Decision**: Default frame analysis at **1 fps** (configurable, hard cap 5 per FR-008). Run GCV face detection on each sampled frame (deterministic, cheap, via the existing gateway). Run the GPT-4o posture batch on a **configurable stride** (default: one 3-frame batch per ~10 s of video) rather than every 3 frames, capping LLM calls. For a 15-min video: ~900 sampled frames, ~90 posture LLM batches.

**Rationale**: The live path is naturally bounded by real-time arrival + dedup; a batch over 15 min has no such limiter, so explicit sampling keeps token cost and wall-clock sane while preserving coverage. Values are config so the demo can tune.

**Alternatives considered**:
- *Analyse every extracted frame with the LLM*: thousands of calls — cost/time prohibitive. Rejected.
- *GCV only, no posture LLM*: loses posture/gesture insights present in the live report. Rejected — sampled LLM keeps parity.

---

## Decision 5 — Processing state on `sessions.status` + `status_detail`

**Decision**: Reuse `sessions.status` (String(32)) for the lifecycle: `PROCESSING` (set when the job starts) → `REPORT_READY` (existing, set by `mark_report_ready`) or `FAILED`. Add a nullable `sessions.status_detail` (Text) for the human-readable failure/clarification reason. `GET /sessions/{id}` returns both; the report endpoint stays gated on the report row existing (unchanged).

**Rationale**: Smallest persistent change; reuses the status the frontend already reads. `status_detail` satisfies FR-009's "human-readable reason".

**Alternatives considered**:
- *New `video_jobs` table*: overkill for one job per session at hackathon scale. Rejected.

---

## Decision 6 — Upload validation + early rejection (FR-002/003)

**Decision**: `POST /sessions/{id}/upload-video` (multipart, `require_session_owner`):
- Reject by extension/content-type allowlist (`.mp4/.mov/.m4v/.webm`, video/* types) → 400 with accepted-formats message.
- Reject size over `VIDEO_MAX_BYTES` (default ~1 GB, configurable) → 413.
- Save to temp, `ffprobe` duration; reject > `VIDEO_MAX_DURATION_S` (900 s) → 400 with the limit. Only then launch the background job and set `status=PROCESSING`; return `202 Accepted`.

**Rationale**: Fast, specific errors before any heavy work (US3); mirrors the existing PPTX upload's validate-then-background shape.

---

## Decision 7 — Demo replay bypass

**Decision**: Under `DEMO_MODE=replay`, the job skips ffmpeg and live AI/STT entirely: VisionAgent/AudioAgent already inject `replay_vision_events` / `replay_audio_events` on their replay branches. The batch driver, when in replay, feeds a small number of synthetic "ticks" so those replay branches fire and write fixture rows, then runs the report. No external calls (SC-006).

**Rationale**: Preserves the demo-safe path uniformly with the live flow; the fixtures already exist.

---

## One-upload-per-session + re-upload (FR-014)

**Decision**: On a new upload for a session, clear that session's prior batch-derived rows (`transcript_entries`, `video_events`, `audio_warnings`, and any existing report) before running, so results replace rather than accumulate. Reuses existing per-phase delete patterns; a small repo helper deletes the session's derived rows.

---

## Summary of changes by file

| File | Change |
|---|---|
| `media/video_decode.py` | NEW — ffprobe duration; ffmpeg frame + PCM extraction (subprocess). |
| `routers/upload_video.py` | NEW — validate (format/size/duration) → background job → 202. |
| `workflows/video_analysis.py` | NEW — extract → analyse(vision‖audio) → flush → report handoff; failure → FAILED. |
| `agents/vision_agent.py` | Additive `ts_ms` override on `on_frame_instant`/`feed_frame`/`_analyse`. |
| `db/models.py` | `Session` + `status_detail` (Text, nullable). |
| `migrations/versions/<new>.py` | Add `status_detail` column. |
| `db/repository.py` | `set_session_status(..., detail=None)`; helper to clear a session's derived rows. |
| `config.py` | `VIDEO_MAX_DURATION_S` (900), `VIDEO_MAX_BYTES`, `VIDEO_ANALYSIS_FPS` (1, cap 5), `VIDEO_POSTURE_STRIDE_S`. |
| `routers/sessions.py` | `GET /sessions/{id}` returns `status_detail`. |
| `app/lib/api.ts` + routes | `uploadVideo()`, `waitForVideoReady()` (poll status), upload UI + states. |
| Deploy image | Install `ffmpeg`. |
| `tests/` | decode (stubbed ffmpeg) + batch (same rows, media ts, replay). |
