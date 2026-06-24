# Implementation Plan: Uploaded Video Batch Analysis

**Branch**: `main` (no feature branch — `git.feature` hook disabled) | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-video-upload-analysis/spec.md`

## Summary

Add a non-live entry point: the presenter uploads one rehearsal video; the backend decodes it with ffmpeg into JPEG frames (≤5 fps) and a PCM 16 kHz mono audio stream, then drives the **existing** VisionAgent and AudioAgent — the same agents the live path uses — to write the same `transcript_entries`, `video_events`, and `audio_warnings` rows. A background `VideoAnalysisWorkflow` orchestrates extract → analyse, then hands off to the existing `ReportWorkflow`. Timestamps come from the video's media timeline (frame position / fps for vision; chunk index × duration for audio, which is already media-relative). Session `status` carries the processing/ready/failed state so the report is gated and the presenter sees progress. Live capture, real-time analysis, and the report flow are untouched.

## Technical Context

**Language/Version**: Python 3.11+ (backend); TypeScript (frontend upload + status polling)
**Primary Dependencies**: FastAPI, Agno Workflow, SQLAlchemy async, existing agents (Vision, Audio, PPTX, Content, Report). **New**: `ffmpeg`/`ffprobe` system binaries (subprocess) for decode + probe — no new Python package.
**Storage**: PostgreSQL — reuse existing rows (`transcript_entries`, `video_events`, `audio_warnings`, `slide_analyses`, `reports`). Add `sessions.status_detail` (Text, nullable) for a human-readable failure reason. Uploaded media handled in a temp file, deleted after analysis.
**Testing**: pytest + pytest-asyncio; ffmpeg invocations stubbed; agents driven with synthetic frames/PCM; assert the same row shapes + media-relative timestamps.
**Target Platform**: Single FastAPI process (local + Railway). ffmpeg must be present on the host/image.
**Project Type**: Web app (Python backend + TanStack Start frontend, monorepo)
**Performance Goals**: Background batch job (not the ≤60s live-end path). Bound vision cost: frame sampling default 1 fps (≤5 cap), GCV per sampled frame, GPT-4o posture batches sampled at a configurable stride. A 15-min video reaches a terminal state without manual intervention.
**Constraints**: Constitution I (live path untouched), II (agent-owned writes), III (session-scoped + token), IV (resilience: bounded, partial-report, replay bypass, terminal failure), V (one new system dependency — justified).
**Scale/Scope**: ≤15-min videos, one upload per session, one background job per upload.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|---|---|---|
| **I. Demo-First Vertical Slices** | ✅ PASS | New entry point; live rehearsal + report flow unchanged (FR-013). Independently demoable: upload → report. |
| **II. Contracted Agent Boundaries** | ✅ PASS | Reuses VisionAgent/AudioAgent — each still writes only its own role-scoped rows and emits completion signals. Batch driver feeds them like `LiveWindowAggregator` does; an additive `ts_ms` override threads media timestamps. No new writer for any table. |
| **III. Session Isolation** | ✅ PASS | Upload + status reads scoped to the owning session, require `access_token` (same as PPTX upload). Report sharing via `share_token` unchanged. |
| **IV. Resilience Before Polish** | ✅ PASS | Background job; per-provider failure handling inherited from agents; partial report; explicit `FAILED` status with reason; `DEMO_MODE=replay` bypasses ffmpeg+AI/STT using fixtures. Live fallbacks untouched. ≤60s SHOULD does not apply (async job, not live-end); progress state mitigates. |
| **V. Native Stack, Minimal Abstractions** | ⚠️ JUSTIFIED | One new dependency: `ffmpeg`/`ffprobe` system binaries. See Complexity Tracking. No new Python package; no new service/queue/storage. |

**Post-design re-check**: All gates pass. Single justified dependency. No constitution amendment required.

## Project Structure

### Documentation (this feature)

```text
specs/003-video-upload-analysis/
├── plan.md              # This file
├── research.md          # Phase 0 decisions
├── data-model.md        # Phase 1 entities
├── quickstart.md        # Phase 1 validation guide
├── contracts/
│   └── video-analysis.md
├── checklists/
│   └── requirements.md  # from /spec-specify
└── tasks.md             # Phase 2 (/spec-tasks — not yet created)
```

### Source Code (repository root)

```text
packages/backend/
├── routers/
│   ├── upload_video.py               # NEW — POST /sessions/{id}/upload-video (validate + background)
│   └── sessions.py                   # GET /sessions/{id} surfaces status_detail
├── media/
│   └── video_decode.py               # NEW — ffprobe duration + ffmpeg frame/audio extraction (subprocess)
├── workflows/
│   └── video_analysis.py             # NEW — VideoAnalysisWorkflow: extract → analyse(vision‖audio) → report handoff
├── agents/
│   ├── vision_agent.py               # additive ts_ms override on on_frame_instant/feed_frame/_analyse
│   ├── audio_agent.py                # unchanged (chunk-index timestamps already media-relative)
│   └── frame_service.py              # reused for dedup of extracted frames
├── db/
│   ├── models.py                     # Session: + status_detail (Text, nullable)
│   └── repository.py                 # set_session_status(session_id, status, detail=None)
├── migrations/versions/
│   └── <new>_add_session_status_detail.py
├── config.py                         # video limits + sampling settings
└── tests/
    ├── test_video_decode.py          # NEW — probe/extract (ffmpeg stubbed)
    └── test_video_analysis.py        # NEW — batch produces same rows, media-timeline ts, replay bypass

packages/web-dashboard/
└── app/
    ├── lib/api.ts                    # uploadVideo() + waitForVideoReady() (poll status)
    └── routes/…                      # upload-video UI + processing/ready/failed states
```

**Structure Decision**: Monorepo unchanged. New code isolated in `media/` (decode), `workflows/video_analysis.py` (orchestration), and `routers/upload_video.py` (entry). The analysis agents and the entire report pipeline are reused as-is; the only agent edit is an additive timestamp override on VisionAgent.

## Triage Framework: [SYNC] vs [ASYNC] Classification

**Execution Strategy**: Hybrid — decode correctness, timestamp mapping, and resilience are human-reviewed ([SYNC]); endpoint, config, frontend, and test scaffolding are delegable ([ASYNC]).

### Preliminary Task Classification

| Task Category | Estimated [SYNC] Tasks | Estimated [ASYNC] Tasks | Rationale |
|---------------|----------------------|----------------------|-----------|
| Business Logic | 2 | 1 | VideoAnalysisWorkflow ordering + vision ts override are correctness-critical (SYNC); audio segmentation helper mechanical (ASYNC). |
| Data Operations | 1 | 1 | status_detail migration/model reviewed (SYNC); repo setter wiring (ASYNC). |
| UI Components | 0 | 2 | Upload control + status states (ASYNC, manual-verified). |
| Integrations | 2 | 0 | ffmpeg decode + ffprobe validation, report handoff (SYNC). |
| Infrastructure | 1 | 0 | ffmpeg present in image/host (SYNC — deploy gate). |

### Triage Decision Criteria Applied

**High-Risk [SYNC] Classifications:**

- ffmpeg decode (broad consumer formats) + ffprobe duration validation.
- VisionAgent media-timeline timestamp override (FR-007 / SC-003).
- VideoAnalysisWorkflow: order, bounded concurrency, agent flush before report read.
- Resilience: terminal FAILED state, partial report, replay bypass.
- ffmpeg availability in the deploy image (feature is inert without it).

**Agent-Delegated [ASYNC] Classifications:**

- PCM segmentation into 2-s chunks.
- `set_session_status` detail plumbing + migration.
- Frontend upload + poll + status UI.
- Test scaffolding with stubbed ffmpeg.

### Triage Audit Trail

| Task | Classification | Primary Criteria | Risk Level | Rationale |
|------|----------------|------------------|------------|-----------|
| ffmpeg/ffprobe decode + probe module | SYNC | Format coverage / correctness | High | Broad codec matrix; wrong output breaks all downstream. |
| Vision ts_ms override | SYNC | Timestamp correctness | High | FR-007/SC-003 depend on it. |
| VideoAnalysisWorkflow | SYNC | Demo path / resilience | High | Ordering + flush-before-report + failure handling. |
| Upload endpoint + validation | SYNC | Session isolation / early reject | Med | Token-scoped; FR-002/003 limits. |
| status_detail migration + model | SYNC | Data contract | Low | One nullable column. |
| Audio PCM segmentation | ASYNC | Mechanical | Low | Pure slicing with tests. |
| Frontend upload + status poll | ASYNC | UI | Med | Manual desktop/mobile verify. |
| Tests (decode, batch) | ASYNC | Validation | Med | ffmpeg stubbed. |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| New dependency: `ffmpeg`/`ffprobe` system binaries | Decode the broad consumer format/codec matrix the user named (YouTube downloads, QuickTime/screen-recorder exports) into JPEG frames + PCM 16 kHz mono — the exact inputs VisionAgent/AudioAgent already accept | Pure-Python decoders (imageio/opencv) cover frames only, not audio extraction, and miss many containers/codecs; PyAV is a compiled ffmpeg wheel that still wraps ffmpeg and adds build burden. Subprocess to the system ffmpeg is simpler and produces agent-ready output directly. |
