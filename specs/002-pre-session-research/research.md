# Phase 0 Research: Pre-Session Topic Research Persistence

**Feature**: `002-pre-session-research` | **Date**: 2026-06-24

All Technical Context unknowns are resolved below. No open NEEDS CLARIFICATION remain.

---

## Decision 1 — Persistence shape: JSONB columns on `sessions`

**Decision**: Add two nullable columns to the existing `sessions` table:
- `research_bundle` (JSONB) — the serialized `ReferenceBundle`.
- `content_research_status` (String(32)) — `full` / `partial` / `skipped` / `not_applicable`.

**Rationale**:
- Mirrors the existing `slides_raw_text` JSONB column on `sessions` already written by `PPTXAgent.persist` → consistent ownership and pattern (Constitution V).
- One-to-one with a session; no need for a child table or join. `ReferenceBundle` is already a Pydantic model that serializes cleanly via `model_dump()`.
- The PPTX agent already owns `sessions` writes (`mark_pptx_ready`), so writing these columns introduces no new writer for the table (Constitution II — one writer per role-scoped table).

**Alternatives considered**:
- *New `session_research` table*: rejected — adds a table, a relationship, and a migration for data that is strictly 1:1 and read once. Violates "minimal abstractions" with no benefit at hackathon scale.
- *Persist on `reports`*: rejected — the report row does not exist until session end; research is produced pre-session.

---

## Decision 2 — Where research runs: a `research` step in `PptxPrepWorkflow`

**Decision**: Insert a `research` step into `PptxPrepWorkflow` between `review` and `write`, so the order is `extract → review → research → write`. `PPTXAgent` gains a `research(topic, topic_context)` phase that returns `(ReferenceBundle, ResearchStatus)`, and `PPTXAgent.persist` writes the bundle + status onto the session row in the same write step as `mark_pptx_ready`.

**Rationale**:
- Keeps the agno Workflow as pure glue (`telemetry=False, db=None`) and keeps writes agent-owned (Constitution II + the Workflow clarification note).
- Research only needs the topic (already on the session), so it does not depend on extract/review output — but placing it just before `write` guarantees it completes before `mark_pptx_ready`.

**Alternatives considered**:
- *Run research in parallel with review*: viable and slightly faster, but adds concurrency to a flow that is already off the real-time path; rejected for MVP simplicity. Can revisit if pre-session latency matters.
- *Separate background task independent of PptxPrepWorkflow*: rejected — would not be covered by the existing `pptx_ready` gate, reintroducing the race the user explicitly wants gone.

---

## Decision 3 — Session-start gating reuses the existing `pptx_ready` poll

**Decision**: No new gating logic. Because `mark_pptx_ready` (which flips `sessions.pptx_ready = true`) runs in the `write` step *after* `research`, and the frontend `waitForPptxReady` (`app/lib/api.ts`) polls `GET /sessions/{id}` for `pptx_ready` before enabling start, session start already waits for research.

**Rationale**: Satisfies FR-006 with zero new code paths — the gate that already blocks start on deck readiness now also covers research because research completes earlier in the same workflow.

**Required adjustment**: `waitForPptxReady` currently times out at 45s. Pre-session now also includes up to `content_research_timeout_s` (default 20s). Bump the frontend poll timeout to ~60s so a slow-but-healthy research fetch does not surface a spurious "deck analysis timed out" error.

**Evidence**:
- `packages/backend/routers/upload.py:40` — `run_pptx_prep_workflow` runs as a FastAPI background task on upload.
- `packages/backend/db/repository.py:40` — `mark_pptx_ready` sets `pptx_ready=True` + `slides_raw_text`.
- `packages/backend/routers/sessions.py:41` — `GET /sessions/{id}` exposes `pptx_ready`.
- `packages/web-dashboard/app/lib/api.ts:66-80` — `waitForPptxReady` polls until `session.pptx_ready`.

---

## Decision 4 — Report-time read path (no live provider calls)

**Decision**: `ContentAnalysisAgent.analyse` reads `session.research_bundle` + `session.content_research_status`; if a bundle is present it reconstructs `ReferenceBundle` and feeds it to the evaluation prompt exactly as today. It MUST NOT call `classify_topic` or `fetch_reference_bundle` at report time. `research_status` comes from the persisted value.

**Rationale**: Removes external-provider latency/failure from the report path (SC-001, SC-003). The evaluation prompt builder (`_build_evaluation_prompt`) already accepts a `ReferenceBundle` + status, so only the source of the bundle changes.

**Fallback (FR-008)**: If `research_bundle` is absent/unreadable (e.g. a session that never ran pre-session prep, or a deck-less session), analysis proceeds transcript-only with `research_status` defaulted to the persisted value or `not_applicable`/`skipped`. No live fetch fallback is added (keeps the "zero calls at report time" guarantee unconditional). This was the user's explicit choice — research is gated to complete pre-session, so the missing-bundle case is an edge, not the norm.

---

## Decision 5 — Demo replay + classification behavior unchanged

**Decision**: Under `DEMO_MODE=replay`, the pre-session research step performs no live fetch and persists a replay-appropriate status (`not_applicable`). Topic classification (`classify_topic`) and the non-technical short-circuit run at pre-session time instead of report time; non-technical/empty topics persist `not_applicable` and skip fetching.

**Rationale**: Preserves Constitution IV demo-safety and the existing classifier semantics; only the timing moves.

---

## Decision 6 — Status surfaced to the report unchanged

**Decision**: `ReportAgent` continues to populate `reports.content_research_status` and the `partial`/`skipped` insight injection, but now sources the value from the persisted session status (via the content payload) rather than from a freshly computed status. The report API field and values are unchanged (FR-013).

**Rationale**: Keeps the report consumer contract stable; the prior feature's status values and insight rules remain the contract.

---

## Summary of changes by file

| File | Change |
|---|---|
| `db/models.py` | `Session`: add `research_bundle` (JSONB, nullable), `content_research_status` (String(32), nullable). |
| `migrations/versions/<new>.py` | Add the two columns; `down_revision = "a1b2c3d4e5f6"`. |
| `db/repository.py` | `mark_pptx_ready` (or a sibling) also persists bundle + status; add getter used by content agent. |
| `agents/pptx_agent.py` | Add `research()` phase; persist bundle + status in `persist()`. |
| `workflows/pptx_prep.py` | Add `research` step (extract → review → research → write). |
| `agents/content_agent.py` | Read persisted bundle/status; remove classify/fetch from report path. |
| `agents/content_research/reference_bundle.py` | Add (de)serialize helpers for JSONB round-trip. |
| `app/lib/api.ts` | Bump `waitForPptxReady` timeout to ~60s. |
| `tests/` | Pre-session persistence test; report-time no-live-call test. |
