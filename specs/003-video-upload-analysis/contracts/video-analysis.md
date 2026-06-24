# Contracts: Uploaded Video Batch Analysis

**Version**: 1.0 | **Date**: 2026-06-24

Public HTTP additions + internal module/agent contracts. The report payload, scoring, and all analysis-row shapes are reused unchanged.

---

## Contract A — `POST /sessions/{session_id}/upload-video` (new HTTP)

**Auth**: `access_token` (session owner), same as `POST /sessions/{id}/upload`.
**Body**: `multipart/form-data`, field `file` = the video.

**Responses**:
| Status | When | Body |
|---|---|---|
| `202 Accepted` | Validated; background analysis started | `{"status": "accepted", "session_id": "<uuid>"}` |
| `400` | Unsupported format | `{"detail": "Only video files accepted: mp4, mov, m4v, webm"}` |
| `400` | Duration > 15 min | `{"detail": "Video too long (max 15 minutes)"}` |
| `413` | Size over limit | `{"detail": "File too large (max <N>MB)"}` |

**Behavior**: validate (extension/content-type → size → ffprobe duration) before launching work; on accept, set `status=PROCESSING`, clear prior derived rows (FR-014), run the background job, return 202.

---

## Contract B — `GET /sessions/{session_id}` (extended response)

Adds `status_detail` to the existing response:

```json
{
  "session_id": "uuid",
  "status": "ACTIVE | PROCESSING | REPORT_READY | FAILED",
  "status_detail": "string | null",
  "topic": "string",
  "pptx_ready": true,
  "started_at": "iso8601",
  "ended_at": "iso8601 | null"
}
```

- Frontend polls this: `PROCESSING` → keep waiting; `REPORT_READY` → open report; `FAILED` → show `status_detail`.
- `GET /sessions/{id}/report` is unchanged — still 404 until the report row exists.

---

## Contract C — `media/video_decode.py` (new internal module)

```python
async def probe_duration_s(path: str) -> float        # ffprobe; raises VideoDecodeError on failure
async def extract_frames(path: str, fps: int, out_dir: str) -> list[tuple[int, str]]
    # ffmpeg -vf fps=<fps>; returns [(index, jpg_path)] ordered; index→ts = index/fps*1000 ms
async def extract_audio_pcm(path: str, out_path: str) -> str
    # ffmpeg -vn -ac 1 -ar 16000 -f s16le; returns out_path (raw PCM 16-bit mono 16kHz)
```

- `fps` clamped to ≤ 5 (FR-008).
- Raises `VideoDecodeError` (caught by the workflow → `FAILED` + reason). Never leaks raw subprocess errors to the client.

---

## Contract D — `VisionAgent` timestamp override (changed, additive)

```python
async def on_frame_instant(self, frame_bytes: bytes, ts_ms: int | None = None) -> None
async def feed_frame(self, frame_bytes: bytes, ts_ms: int | None = None) -> None
# internal: _analyse(frames, ts_ms: int | None = None)
```

- `ts_ms=None` (live) → unchanged: events stamped with `_now_ms()`.
- `ts_ms` provided (batch) → events stamped with the supplied media timestamp.
- No change to `VideoEventPayload` shape or the events written.

---

## Contract E — `VideoAnalysisWorkflow` (new internal orchestration)

**Module**: `workflows/video_analysis.py`

```python
async def run_video_analysis(session_id: uuid.UUID, video_path: str) -> None
```

Steps (agno Workflow, `telemetry=False, db=None`):
1. `set_session_status(PROCESSING)`; clear prior derived rows.
2. **extract**: probe + frames(@fps) + audio PCM into a temp workspace.
3. **analyse** (concurrent, mirrors `LiveAnalysisTeam`):
   - audio: slice PCM into `audio_chunk_seconds` segments → `audio.push_chunk(seg)` in order.
   - vision: for each frame `(idx, bytes)`, dedup via `FrameService`, then `vision.on_frame_instant(bytes, ts)` and `vision.feed_frame(bytes, ts)` where `ts = idx/fps*1000`; posture LLM batch sampled at `VIDEO_POSTURE_STRIDE_S`.
4. **flush**: `vision.aclose()`, `audio.aclose()`.
5. **report**: `build_report_agent(orch).generate(session_id)`; `orch.mark_report_ready(session_id)`.
- Any exception → `set_session_status(FAILED, reason)`; always reaches a terminal state; temp workspace removed in `finally`.
- `DEMO_MODE=replay` → skip extract + live AI/STT; drive replay branches to write fixtures, then report (SC-006).

---

## Contract F — Repository (extended)

```python
async def set_session_status(self, session_id, status: str, detail: str | None = None) -> None
async def clear_session_derived_rows(self, session_id) -> None
    # delete transcript_entries, video_events, audio_warnings, and the reports row for the session
```

- `set_session_status` writes `status` (+ `status_detail = detail`).
- `clear_session_derived_rows` supports re-upload replacement (FR-014).

---

## Migration

**File**: `migrations/versions/<rev>_add_session_status_detail.py`

```python
def upgrade():
    op.add_column("sessions", sa.Column("status_detail", sa.Text(), nullable=True))
def downgrade():
    op.drop_column("sessions", "status_detail")
```
(`down_revision` = current head: `b2c3d4e5f6a7`.)

---

## Deploy

- `ffmpeg` (incl. `ffprobe`) MUST be installed in the runtime image / host. Without it, `probe_duration_s`/`extract_*` raise `VideoDecodeError` → upload returns/records a clear failure rather than crashing.
