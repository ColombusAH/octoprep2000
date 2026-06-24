# Quickstart & Validation: Uploaded Video Batch Analysis

**Feature**: `003-video-upload-analysis` | **Date**: 2026-06-24

Validates that an uploaded rehearsal video is analysed in batch and produces the same report as a live session, with media-timeline timestamps and safe degradation.

## Prerequisites

```bash
# ffmpeg + ffprobe must be on PATH
ffmpeg -version && ffprobe -version       # macOS: brew install ffmpeg

make db-up
make db-migrate          # applies the status_detail migration
make dev                 # backend :8000 + frontend :3000
```

Backend tests (ffmpeg stubbed — no real decode needed):

```bash
cd packages/backend && uv run pytest tests/test_video_decode.py tests/test_video_analysis.py -q
```

## Scenario 1 — Upload → same report (US1, FR-001/004/005/006)

1. Create a session and upload a PPTX; wait for `pptx_ready`.
2. `POST /sessions/{id}/upload-video` with a short MP4 of a person speaking to slides → expect `202`.
3. Poll `GET /sessions/{id}` until `status` is `REPORT_READY`.
4. `GET /sessions/{id}/report`.

**Expected**: report has voice, body, slide, content scores and insights — same structure as a live-session report. Voice insights reflect the spoken audio (transcript/pacing/fillers); body insights reflect the on-camera frames.

## Scenario 2 — Timestamps map to the video (FR-007, SC-003)

1. After Scenario 1, inspect insight timestamps and the rows:
   ```sql
   SELECT min(start_ms), max(end_ms) FROM transcript_entries WHERE session_id='<id>';
   SELECT min(timestamp_ms), max(timestamp_ms) FROM video_events WHERE session_id='<id>';
   ```

**Expected**: all timestamps fall within `[0, video_duration_ms]` and line up with moments in the recording (not wall-clock processing time).

## Scenario 3 — Progress + terminal states (US2, FR-009/010, SC-005)

1. Immediately after upload, `GET /sessions/{id}` → `status: PROCESSING`; `GET .../report` → `404`.
2. After completion → `status: REPORT_READY`, report available.
3. Force a failure (e.g. upload a corrupt file that passes extension check) → `status: FAILED`, `status_detail` has a human-readable reason; never stuck on `PROCESSING`.

## Scenario 4 — Early rejection (US3, FR-002/003, SC-004)

1. Upload a `.txt` → `400`, message names accepted formats.
2. Upload a >15-min video → `400`, message states the limit. (No analysis starts.)
3. Upload an oversize file → `413`.

## Scenario 5 — Resilience: provider failure → partial report (FR-011)

1. With STT or vision provider unavailable, upload a valid video.

**Expected**: job completes to `REPORT_READY` with a partial report (whatever modalities succeeded), or `FAILED` with a reason if nothing usable — never an unhandled crash, and other sessions/live path unaffected.

## Scenario 6 — Demo replay bypass (FR-012, SC-006)

1. Set `DEMO_MODE=replay`, restart backend.
2. Upload any small valid video, wait for `REPORT_READY`, view report.

**Expected**: report built from fixtures; no ffmpeg decode of real content and no live AI/STT calls.

## Scenario 7 — Live path untouched (FR-013)

1. Run a normal live rehearsal (WS capture) end-to-end and confirm its report still generates as before.

## Reference

- Data model: [data-model.md](./data-model.md)
- Contracts: [contracts/video-analysis.md](./contracts/video-analysis.md)
- Spec: [spec.md](./spec.md)
