# Data Model: Uploaded Video Batch Analysis

**Feature**: `003-video-upload-analysis` | **Date**: 2026-06-24

## Overview

The batch path writes the **same** rows the live path writes; the only persistent schema change is one nullable column on `sessions` for a failure/processing reason. No new analysis tables. Uploaded media and extracted frames/audio are transient (temp workspace), not persisted.

---

## Extended: `Session` (table `sessions`)

Existing columns unchanged. Added:

| Field | Type | Nullable | Description |
|---|---|---|---|
| `status_detail` | Text | yes | Human-readable detail for the current `status` — primarily the failure reason when `status = FAILED`. `null` otherwise. |

**`status` values used by this feature** (column already `String(32)`, no migration for values):

| Value | Meaning |
|---|---|
| `ACTIVE` | Existing default (created / live). |
| `PROCESSING` | Batch video analysis running (set when the job starts). |
| `REPORT_READY` | Existing terminal-success (set by `mark_report_ready`). |
| `FAILED` | Batch analysis failed; `status_detail` holds the reason. |

**Writer**: `Orchestrator.set_session_status` / repository (existing owner of session-status writes). The batch driver sets `PROCESSING`/`FAILED`; the existing report path sets `REPORT_READY`.

---

## Reused (NOT new) — rows the batch path produces

Identical in shape to the live path; the report is assembled from them unchanged.

| Table | Producing agent | Timestamp source (batch) |
|---|---|---|
| `transcript_entries` | AudioAgent | `chunk_index * audio_chunk_seconds * 1000` (start/end) — already media-relative |
| `audio_warnings` | AudioAgent | derived from chunk timing (filler/WPM) — media-relative |
| `video_events` | VisionAgent | **`ts_ms` override** = `frame_index / analysis_fps * 1000` (media-relative) |
| `slide_analyses` | PPTXAgent (pre-session, unchanged) | n/a |
| `reports` | ReportAgent (unchanged) | n/a |

**Key invariant (FR-007/SC-003)**: every `video_events.timestamp_ms` and `transcript_entries.start_ms/end_ms` for a batch session falls within `[0, video_duration_ms]` and corresponds to the position in the recording.

---

## Transient entities (not persisted)

### Uploaded Rehearsal Video
The submitted file. Validated then written to a temp path; deleted after the job. Attributes used: detected format (extension/content-type), size (bytes), duration (from ffprobe). Bounds: format ∈ allowlist; size ≤ `VIDEO_MAX_BYTES`; duration ≤ `VIDEO_MAX_DURATION_S` (900 s).

### Extraction Workspace
Temp directory holding extracted JPEG frames (`frame_%06d.jpg` at `analysis_fps`) and the PCM 16 kHz mono audio stream. Removed in a `finally` after analysis (success or failure).

### Frame / Audio-segment streams (in-memory)
- Frames: ordered `(index, bytes)` → media ts `index/fps`.
- Audio: PCM sliced into `audio_chunk_seconds` segments in order → fed to `AudioAgent.push_chunk`.

---

## State transitions: session lifecycle (batch path)

```text
[create]                    ──▶ ACTIVE
[upload validated, job starts] ──▶ PROCESSING
[analyse + report succeed]  ──▶ REPORT_READY        (status_detail = null)
[unrecoverable failure]     ──▶ FAILED              (status_detail = reason)
[re-upload]                 ──▶ PROCESSING          (prior derived rows cleared first)
```

- The report endpoint returns 404 until the `reports` row exists; `PROCESSING` therefore reads as "report not ready" (FR-010).
- Every job ends `REPORT_READY` or `FAILED` — never stuck in `PROCESSING` (SC-005); the background task sets a terminal state in all paths.

---

## Configuration (environment)

| Variable | Default | Purpose |
|---|---|---|
| `VIDEO_MAX_DURATION_S` | `900` | Max accepted duration (15 min). |
| `VIDEO_MAX_BYTES` | ~`1_073_741_824` | Max upload size. |
| `VIDEO_ANALYSIS_FPS` | `1` | Frame sampling rate (hard cap 5 — FR-008). |
| `VIDEO_POSTURE_STRIDE_S` | `10` | Seconds between GPT-4o posture batches (cost bound). |

---

## Validation rules

- Reject non-allowlisted format / oversize before any decode (FR-002/003).
- `analysis_fps` is clamped to ≤ 5 regardless of config (FR-008).
- A new upload clears the session's prior `transcript_entries`, `video_events`, `audio_warnings`, and `reports` row before running (FR-014).
- The job MUST set a terminal `status` in a `finally`/except path; a crash mid-decode → `FAILED` + reason, never an unhandled background exception (FR-011, SC-005).
- One analysis path per session: uploading a video is the analysis source; mixing with a live rehearsal is out of scope (Assumptions).
