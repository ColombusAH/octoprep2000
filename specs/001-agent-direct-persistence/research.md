# Phase 0 Research: Agent-Owned Persistence

**Feature**: 001-agent-direct-persistence
**Date**: 2026-06-24

## Context recap (from current code)

- `Orchestrator` (`packages/backend/orchestrator/orchestrator.py`) is the **sole DB writer**
  for live data. Agents emit typed Pydantic payloads via `on_video_event`, `on_transcript`,
  `on_audio_warning`, `on_slide_analysis`, `on_report`; the Orchestrator persists them with a
  fresh `AsyncSession` per write (`_with_repo`, lines 48-51).
- The Orchestrator also: owns the **video-event batch buffer** (flush every 1s or N=20,
  lines 36-37, 190-204), **publishes live feedback** to `broadcaster`
  (`core/feedback_broadcaster.py`), and owns **audio-only fallback** (lines 171-187).
- **Report assembly already reads from the DB**, not from agent payloads: `ReportAgent.generate`
  reads transcript / video_events / audio_warnings / slide_analyses via the repository
  (`agents/report_agent.py:35-40`); `ContentAnalysisAgent.analyse` reads transcript
  (`agents/content_agent.py:38-43`). Both own their own `AsyncSession` via `get_session_maker()`.
- Report is triggered by `POST /sessions/:id/end` (`routers/sessions.py:46-63`), which ends the
  session, builds the report by reading the DB, then persists via `on_report`.
- Ingress already goes "direct to agent" for video (FrameService → `VisionAgent.push_frame`) and
  audio (`AudioAgent.push_chunk`); PPTX runs as a background task calling `PPTXAgent.analyse`.

**Conclusion**: the only thing routing "through the Orchestrator as a data pipe" is the **write
step** of live data. The read side of the agreed place (DB) is already in place. The feature is
therefore a **write-ownership move plus a completion-signal contract**, not a new data pipeline.

---

## Decision 1 — "The agreed place" = existing PostgreSQL tables

**Decision**: Agents write to, and the Orchestrator reads from, the existing Postgres tables
(`video_events`, `transcript_entries`, `audio_warnings`, `slide_analyses`,
`sessions.slides_raw_text` / `sessions.pptx_ready`, `reports`). No new store, no schema change.

**Rationale**: Constitution Principle V (Native Stack, Minimal Abstractions) forbids new
infrastructure without a proven constraint. The tables and repository read methods already exist
and are already the report's source of truth. The user's phrase "agreed place" maps cleanly to
these tables.

**Alternatives considered**:
- New event queue / Redis pub-sub for hand-off — rejected: new infra, violates Principle V,
  single-process app has no need.
- In-memory shared buffer the Orchestrator drains — rejected: not durable, loses the user's
  explicit "put it on the DB" requirement, and weakens crash-resilience.

---

## Decision 2 — Each agent owns its writes via a shared persistence helper

**Decision**: Introduce a thin reusable write helper (an `AgentPersistence` mixin/util that wraps
`get_session_maker()` + `PostgreSQLRepository`, mirroring the Orchestrator's `_with_repo`). Each
agent uses it to persist exactly the rows it produces:
- `VisionAgent` → `bulk_insert_video_events` (keeps batching, see Decision 4)
- `AudioAgent` → `insert_transcript_entry`, `insert_audio_warning`
- `PPTXAgent` → `insert_slide_analyses` + `mark_pptx_ready`
- `ReportAgent` → `insert_report` (it already reads; now it also owns the write that
  `Orchestrator.on_report` did)

**Rationale**: Reuses the proven fresh-session-per-write pattern (B2 fix) already used by
Orchestrator, ReportAgent, and ContentAgent. No new dependency. Keeps each agent's writes scoped
to its own table(s), so concurrent agents never contend on the same rows.

**Alternatives considered**:
- Give every agent a long-lived `AsyncSession` — rejected: the B2 fix exists specifically to avoid
  request-scoped session capture; reintroducing it risks cross-request races.
- Keep writes in the repository but call it directly without a helper — acceptable, but the helper
  centralizes session lifecycle + error logging and matches existing style.

---

## Decision 3 — Completion-signal contract: in-process notification to the Orchestrator

**Decision**: Add a single Orchestrator method `notify_complete(session_id, kind, meta=None)` where
`kind ∈ {VIDEO, AUDIO, PPTX, CONTENT, REPORT}` (a `CompletionKind` Literal). Agents call it after a
durable write. The Orchestrator records per-session completion state in memory and uses it to:
(a) know PPTX is persisted, (b) ensure the final video flush is durable before report read.
"Notification" is a direct async method call — no broker (Principle V).

**Rationale**: The app is single-process asyncio; a method call IS the event bus. This matches how
agents already call `orchestrator.on_*` and `orchestrator.activate_fallback`. The signal makes the
"notify that they finished processing" requirement explicit and testable without new infra.

**Alternatives considered**:
- DB status column per data-kind that the Orchestrator polls — rejected: polling adds latency and a
  schema change for no benefit in a single process.
- Broadcaster event for completion — rejected: the broadcaster is the *client-facing* channel;
  reusing it for internal coordination muddies the contract.

---

## Decision 4 — Video-event batching moves to VisionAgent

**Decision**: Move `VIDEO_BUFFER_MAX` (20) and the 1s periodic flush from the Orchestrator into
`VisionAgent`. The agent buffers events, flushes on size/interval, and on each flush emits the live
feedback to the broadcaster per event and calls `notify_complete(..., kind="VIDEO")` after a durable
batch write. `end_session` triggers a final agent flush before the report reads video_events.

**Rationale**: Batching is a property of the *writer*. With writes owned by the agent, the buffer
must live with the writer to preserve the §10b.5 write-volume guarantee (FR-009). Keeps the exact
same flush thresholds → no DB-write-volume regression.

**Alternatives considered**:
- Leave batching in the Orchestrator and have it be the only video writer — rejected: contradicts
  the feature (Orchestrator would still own that write).

---

## Decision 5 — Who publishes live feedback to the broadcaster

**Decision**: The producing agent publishes its own live-feedback events directly to `broadcaster`
(`VisionAgent` for video events, `AudioAgent` for audio warnings). The Orchestrator retains only
the lifecycle broadcasts it already owns conceptually: `REPORT_READY` and `FALLBACK_ACTIVATED`.

**Rationale**: Live feedback is a side-effect of the agent producing an event; co-locating publish
with the write keeps one owner per event. The outbound `FeedbackEvent` shape (shared-types) is
**unchanged**, so the frontend contract and `DEMO_MODE=replay` behavior are preserved (FR-008).

**Alternatives considered**:
- Keep all broadcaster publishing in the Orchestrator via a broadcast-only method — viable and lower
  churn, but leaves the Orchestrator on the live hot path the feature wants to remove. Documented as
  the fallback option if agent-side publish proves noisy during implementation.

---

## Decision 6 — Governance: Constitution Principle II must be amended first

**Decision**: Treat the Principle II conflict as a hard pre-implementation gate. Before code lands,
amend Principle II ("Contracted Agent Boundaries") to permit **agents writing their own role-scoped
rows**, while retaining the rest of the boundary (typed contracts, no agent-to-agent coupling,
explicit session scope, versionable WS payloads).

**Rationale**: Principle II currently states "The Orchestrator MUST own all writes to PostgreSQL …
Agents MUST NOT bypass the Orchestrator for writes." This feature directly contradicts that. The
constitution governs the gate; shipping against it without amendment is an unjustified violation.

**Proposed amended wording (for the amendment task, not applied here)**: "Each agent MAY write only
the rows for its own role through the typed repository, and MUST signal completion to the
Orchestrator. The Orchestrator owns session lifecycle, cross-agent coordination, and report
assembly by reading the agreed tables. Agents MUST NOT write another agent's tables or couple
directly to unrelated agents. Shared WebSocket payload types MUST remain explicit and versionable."

**Alternatives considered**:
- Scoped one-feature exception instead of amendment — acceptable as a faster path, but an amendment
  is cleaner because the new model becomes the standing architecture.
