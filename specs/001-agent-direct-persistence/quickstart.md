# Quickstart / Validation: Agent-Owned Persistence

**Feature**: 001-agent-direct-persistence

Run guide proving the new flow end-to-end. Implementation details live in `tasks.md` (after
`/spec-tasks`); this file is the validation harness.

## Prerequisites

- `make install` done; `make db-up` running (Postgres 15).
- `.env` present. For deterministic validation use `DEMO_MODE=replay` (no live Vision/STT calls).
- Constitution Principle II amendment merged (governance gate, FR-013) — required before this
  feature's code is considered shippable.

## Setup

```bash
make db-up
DEMO_MODE=replay make backend     # port 8000
make frontend                     # port 3000 (optional, for UI path)
```

## Scenario 1 — Live capture written by owning agents (US1, SC-001)

1. Create a session: `POST /sessions` → capture `session_id` + `access_token`.
2. Open the video + audio WebSockets and stream (or drive replay fixtures).
3. **Expected**: rows appear in `video_events`, `transcript_entries`, `audio_warnings`.
4. **Assert ownership**: with logging on, the write log lines originate from VisionAgent /
   AudioAgent, not from `Orchestrator.on_*`. Orchestrator performs **zero** writes for these tables.
   - Code-level check: `Orchestrator` no longer references `bulk_insert_video_events`,
     `insert_transcript_entry`, `insert_audio_warning`.

## Scenario 2 — Completion signals + Orchestrator reads agreed place (US2, SC-002)

1. During the session, each agent emits `notify_complete(session_id, kind)` after its commits.
2. End the session: `POST /sessions/:id/end`.
3. **Expected**: VisionAgent flushes final batch before the report reads `video_events`; ReportAgent
   assembles the report purely from DB reads; session → `REPORT_READY`.
4. `GET /sessions/:id/report` returns scores + insights.

## Scenario 3 — PPTX persisted by its agent (US3)

1. `POST /sessions/:id/upload` with a `.pptx`.
2. **Expected**: PPTXAgent writes `slides_raw_text` first, then `slide_analyses`, then signals PPTX.
3. Poll `GET /sessions/:id` until `pptx_ready=true` — reflects the agent's own write.

## Scenario 4 — Baseline equivalence (US1/FR-011, SC-003)

1. Capture a `git stash`/pre-change baseline report for a fixed replay session.
2. Run the same replay session post-change.
3. **Expected**: same overall/voice/body/slide/content scores and insight set (within existing
   dedup/scoring tolerance). No user-visible report regression.

## Scenario 5 — Resilience preserved (FR-010, SC-005/SC-006)

- `DEMO_MODE=replay` full run completes (SC-005).
- Force 3 consecutive Vision timeouts (non-replay) → `FALLBACK_ACTIVATED` broadcast, body score
  omitted, report reweights to voice 0.40 / slide 0.30 / content 0.30 (SC-006).
- Kill an agent mid-write → session does not falsely report fully processed; report degrades via
  neutral defaults.

## Scenario 6 — Docs + presentation match (US4, SC-007)

- `docs/TECH-ARCHITECTURE-C4.md`: sequence/flow sections describe direct-to-agent writes +
  completion signals; **no** "Orchestrator is sole writer" statements remain.
- `docs/presentation/ARCHITECTURE-DECK.html`: architecture slide diagram + narration match new flow.
- Grep gate: `grep -ri "sole writer" docs/` returns nothing describing the live flow.

## Run tests / lint

```bash
make test
make lint
```
