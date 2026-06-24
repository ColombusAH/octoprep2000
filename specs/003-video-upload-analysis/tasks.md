# Tasks: Uploaded Video Batch Analysis

**Feature**: `003-video-upload-analysis` | **Plan**: [plan.md](./plan.md) | **Branch**: `main`

Minimum task set (per request). Reuses existing agents + report pipeline; new code is decode, one workflow, one endpoint. Tests folded into one task covering the key invariants (same rows, media-timeline timestamps, replay).

**Path note**: backend under `packages/backend/`; frontend under `packages/web-dashboard/`.

---

## Phase 1: Setup

- [X] T001 Ensure `ffmpeg` (+ `ffprobe`) is installed in the runtime image and dev docs: add `ffmpeg` to the Railway/Docker build and note `brew install ffmpeg` in `README`/quickstart. Feature is inert without it.

---

## Phase 2: Foundational (blocking)

- [X] T002 [P] Add video config to `packages/backend/config.py`: `video_max_duration_s=900`, `video_max_bytes` (~1 GB), `video_analysis_fps=1` (clamp ≤5), `video_posture_stride_s=10`.
- [X] T003 Add `status_detail` (Text, nullable) to `Session` in `packages/backend/db/models.py`; create migration `packages/backend/migrations/versions/<rev>_add_session_status_detail.py` (`down_revision="b2c3d4e5f6a7"`); extend `set_session_status(session_id, status, detail=None)` and add `clear_session_derived_rows(session_id)` (delete transcript_entries, video_events, audio_warnings, reports row) in `packages/backend/db/repository.py` — Contracts B/F.
- [X] T004 Create `packages/backend/media/video_decode.py`: `probe_duration_s`, `extract_frames(path, fps, out_dir)` (clamp fps ≤5; returns ordered `(index, jpg_path)`), `extract_audio_pcm` (PCM s16le 16kHz mono) via ffmpeg/ffprobe subprocess; raise `VideoDecodeError` on failure — Contract C.
- [X] T005 Add additive `ts_ms: int | None = None` override to `on_frame_instant`, `feed_frame`, and `_analyse` in `packages/backend/agents/vision_agent.py`: when provided, stamp events with `ts_ms` instead of `_now_ms()`; live callers (no arg) unchanged — Contract D.

---

## Phase 3: User Story 1 — Upload a recorded rehearsal, get the same report (P1)

**Goal**: One uploaded video → same report as live, with media-timeline timestamps.

**Independent test**: Create session, upload PPTX, `POST /sessions/{id}/upload-video` → poll `status` → `REPORT_READY` → report has voice/body/slide/content, timestamps within video duration, zero changes to live path.

- [X] T006 [US1] Create `packages/backend/workflows/video_analysis.py` — `run_video_analysis(session_id, video_path)`: set `PROCESSING` + `clear_session_derived_rows`; extract (probe + frames@fps + PCM); analyse concurrently (audio: slice PCM into `audio_chunk_seconds` segments → `audio.push_chunk` in order; vision: per frame dedup via `FrameService` → `on_frame_instant(bytes, ts)` + `feed_frame(bytes, ts)`, `ts=index/fps*1000`, posture batch sampled at `video_posture_stride_s`); `vision.aclose()`/`audio.aclose()`; then `build_report_agent(orch).generate(session_id)` + `orch.mark_report_ready`; any exception → `set_session_status(FAILED, reason)`; temp workspace removed in `finally`; `DEMO_MODE=replay` skips extract + live AI/STT and drives replay branches — Contract E (FR-007/011/012/014, SC-003/005/006).
- [X] T007 [US1] Create `packages/backend/routers/upload_video.py` — `POST /sessions/{id}/upload-video` (multipart, `require_session_owner`): validate format allowlist → size → `ffprobe` duration (reject with 400/413 + specific messages); save temp; launch `run_video_analysis` as background task; return `202`. Register router in the app. Covers US3 early rejection (FR-002/003) and sets `PROCESSING` — Contract A.

---

## Phase 4: User Story 2 — Track processing progress (P2)

**Goal**: Presenter sees processing / ready / failed.

**Independent test**: After upload, `GET /sessions/{id}` shows `PROCESSING`, then `REPORT_READY` (or `FAILED` with reason); report 404 until ready.

- [X] T008 [US2] Add `status_detail` to the `GET /sessions/{id}` response in `packages/backend/routers/sessions.py` (status already returned) — Contract B (FR-009/010).

---

## Phase 5: Polish & cross-cutting

- [X] T009 [P] Frontend in `packages/web-dashboard/app/`: add `uploadVideo(sessionId, file)` + `waitForVideoReady(sessionId)` (poll `GET /sessions/{id}` for `REPORT_READY`/`FAILED`) in `lib/api.ts`, and an upload-video control + processing/ready/failed states (text, not color-only) in the session route.
- [X] T010 Tests in `packages/backend/tests/`: `test_video_decode.py` (ffmpeg/ffprobe stubbed — fps clamp, ordered frames, `VideoDecodeError` on failure); `test_video_analysis.py` (batch writes transcript_entries/video_events/audio_warnings with media-timeline timestamps within duration; failure → `FAILED` + detail, never stuck; `DEMO_MODE=replay` makes no live calls).

---

## Dependencies

```text
T001 (deploy, independent)
T002 ─┐
T003 ─┼─▶ T006 ─▶ T007 ─▶ T008 ─▶ T010
T004 ─┤        ▲
T005 ─┘────────┘ (ts override consumed by workflow)
T009 [P] (frontend, independent of backend tasks)
```

- T002–T005 foundational; T002/T004/T005 parallelizable ([P] where different files), T003 reviewed.
- T006 needs T002+T003+T004+T005. T007 needs T006. T008 after T003. T010 last.
- T001 and T009 independent ([P]).

## Parallel opportunities

- T002 ∥ T004 ∥ T005 (different files).
- T001 (deploy) and T009 (frontend) ∥ everything.

## MVP scope

US1 (T001–T007) delivers the feature: upload → batch analysis → same report, gated by `status`. US2 (T008) is a one-field visibility add; US3 validation is folded into T007. T009 (frontend) + T010 (tests) harden + validate.
