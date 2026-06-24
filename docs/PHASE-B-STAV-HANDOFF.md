# Phase B — Slide Timeline Handoff (Stav branch)

Phase B adds a **manual slide timeline** during rehearsal, **live `STALE_SLIDE` warnings**, and **time-aligned delivery analysis** at session end. Phase A (semantic-only delivery) remains as fallback when no slide events exist.

## What Stav shipped on this branch

| Area | Status |
|------|--------|
| `slide_events` table + Alembic migration `f3a8c1d902ef` | Done |
| `SlideEventPayload` contract (`schemas.py` + `shared-types`) | Done |
| `POST`-less WS ingest `/slide-stream` | Done |
| `PPTXAgent.record_slide_event()` + in-memory slide state | Done |
| `PPTXAgent.analyse_delivery()` v2 (timeline when events present) | Done |
| `ReportAgent.generate()` reads events + replay fallback | Done |
| `GET /sessions/:id` → `slide_count` | Done |
| Session UI slide tracker + `connectSlide()` | Done (Ortal lane, implemented here for E2E) |
| `AudioAgent` `STALE_SLIDE` | Done (Or Yam lane, implemented here for E2E) |
| Report dedupe by `analysis_phase` | Done (Avner lane) |
| Replay fixtures: `slide_events.json`, audio `STALE_SLIDE` | Done |

## WS contract (frozen)

**Route:** `ws://localhost:8000/slide-stream?session_id={uuid}&token={access_token}`

**Client → server** (JSON text frame):

```json
{ "slide_index": 3, "timestamp_ms": 125000, "source": "manual" }
```

| Field | Rule |
|-------|------|
| `slide_index` | 1-based, `≤ slide_count` |
| `timestamp_ms` | Ms since recording start (same origin as audio chunk clock) |
| `source` | `"manual"` \| `"keyboard"` |

**First event:** `{ "slide_index": 1, "timestamp_ms": 0 }` when recording starts.

**Server:** rejects out-of-order timestamps; closes with `4000` if no deck uploaded.

## Integration table — who wires what

| Symbol / API | Owner | Action |
|--------------|-------|--------|
| `connectSlide()` in [`packages/web-dashboard/app/lib/ws.ts`](../packages/web-dashboard/app/lib/ws.ts) | **@Ortal** | Connect at recording start; send JSON on slide change. **Implemented on branch** — review UX copy/layout. |
| Slide tracker UI on [`session.$id.tsx`](../packages/web-dashboard/app/routes/session.$id.tsx) | **@Ortal** | ←/→ buttons, number keys 1–9, “Slide N / M”. **Implemented on branch**. |
| `GET /sessions/:id` → `slide_count` | **@Ortal** | Bound tracker; hide when `null`. **Backend done**; frontend reads it on load. |
| `SlideEventMessage` type in [`shared-types`](../packages/shared-types/src/index.ts) | **@Ortal** | Import in FE instead of local duplicate if you add `@octoprep/shared-types` dep. |
| `PPTXAgent.record_slide_event()` | **@Stav** | Called from [`slide_ws.py`](../packages/backend/routers/slide_ws.py) only — frontend must not call HTTP directly. |
| `PPTXAgent.get_slide_state(now_ms)` | **@Or Yam** | Returns `{ slide_index, since_ms, dwell_ms }` for live checks. Wired via `SessionRuntime`. |
| `AudioAgent._check_stale_slide()` | **@Or Yam** | Emits `STALE_SLIDE` → DB + `/realtime-feedback`. **Implemented on branch** — tune threshold via `STALE_SLIDE_SECONDS`. |
| `ReportAgent.generate()` slide_events read | **@Stav** | Reads DB; replay uses `replay_slide_events()` when `DEMO_MODE=replay`. |
| `ReportAgent._score_slides()` dedupe key | **@Avner** | Groups by `(factor, type, analysis_phase)`. **Done on branch**. |
| `Orchestrator.set_active_slide()` (optional) | **@Avner** | Not needed — state lives on `PPTXAgent` instance in `SessionRuntime`. |
| `ContentAnalysisAgent` | **@Dean** | No Phase B changes — still read-only context in delivery prompt. |
| Vision pipeline | **@Naor** | No Phase B changes. |

## Environment

```bash
make db-migrate   # applies f3a8c1d902ef_add_slide_events
make dev
```

Optional in `.env`:

```
STALE_SLIDE_SECONDS=240   # default — dwell before STALE_SLIDE toast
```

## Manual test flow

1. Upload a PPTX on `/start`, wait for analysis.
2. Open `/session/:id` — sidebar shows deck slide count.
3. Start Recording — tracker appears; slide 1 sent at `t=0`.
4. Use ←/→ or number keys while speaking; enable live feedback toggle **before** start to see toasts.
5. Stay on one slide >4 min (or lower `STALE_SLIDE_SECONDS` for testing) → `STALE_SLIDE` toast.
6. End Session → report includes **While presenting:** delivery insights (time-aligned when events exist).

## Replay test

```bash
DEMO_MODE=replay make dev
# Run a full session end — delivery uses slide_events.json + slide_delivery_findings.json
```

## Key functions (Stav)

| Function | File |
|----------|------|
| `build_slide_timeline()` | `agents/pptx_agent.py` |
| `format_time_aligned_transcript()` | `agents/pptx_agent.py` |
| `PPTXAgent.build_delivery_dump()` | `agents/pptx_agent.py` — timeline branch when `timeline` set |
| `PPTXAgent.analyse_delivery(..., slide_events=)` | `agents/pptx_agent.py` |
| `PPTXAgent.record_slide_event()` | `agents/pptx_agent.py` |
| `PPTXAgent.get_slide_state()` | `agents/pptx_agent.py` |
| `replay_slide_events()` | `agents/replay_fixtures.py` |
| `insert_slide_event` / `read_slide_events` | `db/repository.py` |

## Tests added

- `tests/test_pptx_agent.py` — timeline, aligned transcript, `record_slide_event`
- `tests/test_slide_ws.py` — WS auth + no-deck close
- `tests/test_audio_stale_slide.py` — STALE_SLIDE emission
- `tests/test_report_dedup.py` — static vs delivery not merged

Run: `make test` from repo root.
