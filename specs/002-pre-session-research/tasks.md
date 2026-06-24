# Tasks: Pre-Session Topic Research Persistence

**Feature**: `002-pre-session-research` | **Plan**: [plan.md](./plan.md) | **Branch**: `main`

Minimum task set (per request). No new dependencies, no Setup phase needed. Tests folded into one task covering the constitution-mandated invariants (SC-001 + resilience).

**Path note**: all backend paths under `packages/backend/`; frontend under `packages/web-dashboard/`.

---

## Phase 1: Foundational (blocking — persistence layer)

- [X] T001 Add `research_bundle` (JSONB, nullable) and `content_research_status` (String(32), nullable) to `Session` in `packages/backend/db/models.py`, and create migration `packages/backend/migrations/versions/<rev>_add_session_research.py` adding both columns with `down_revision = "a1b2c3d4e5f6"` (see [contracts/session-research.md](./contracts/session-research.md) Migration).
- [X] T002 [P] Add `to_jsonb(bundle)` and `from_jsonb(data)` helpers to `packages/backend/agents/content_research/reference_bundle.py` (`model_dump()` / `ReferenceBundle(**data)`; `from_jsonb(None|invalid) → None`, logged) — Contract F.
- [X] T003 Extend `mark_pptx_ready` in `packages/backend/db/repository.py` to also set `research_bundle` and `content_research_status` in the same commit that flips `pptx_ready` — Contract D.

---

## Phase 2: User Story 1 — Persisted research reused at report time (P1)

**Goal**: Research runs + persists during pre-session prep; content analyser reuses it with zero live provider calls. Gating reuses the existing `pptx_ready` poll.

**Independent test**: Upload a technical-topic deck → `pptx_ready` flips only after research saved → end session → report reflects reference material with no Context7/Exa calls.

- [X] T004 [US1] Add `research(topic, topic_context)` phase to `PPTXAgent` in `packages/backend/agents/pptx_agent.py`: demo-replay/non-technical/empty → `(None, "not_applicable")`; technical → `fetch_reference_bundle` + `compute_research_status`; never raises — Contract A. Covers US3 non-technical skip (FR-005).
- [X] T005 [US1] Extend `PPTXAgent.persist` in `packages/backend/agents/pptx_agent.py` to accept `bundle` + `research_status` and persist them via the extended `mark_pptx_ready` (T003), preserving `notify_complete("PPTX")` after commit — Contract C.
- [X] T006 [US1] Add a `research` step to `packages/backend/workflows/pptx_prep.py` ordered `extract → review → research → write`; wrap it so any exception/timeout yields `(None, "skipped")` and the `write` step still runs (FR-006/FR-007 resilience) — Contract B. Thread bundle+status from research step into the write step.
- [X] T007 [US1] Rewrite the research path in `ContentAnalysisAgent.analyse` (`packages/backend/agents/content_agent.py`) to read `session.research_bundle` (via `from_jsonb`) + `session.content_research_status`; remove `classify_topic`/`fetch_reference_bundle` calls — no live provider calls at report time; null/invalid bundle → transcript-only (FR-008) — Contract E.

---

## Phase 3: Polish & cross-cutting

- [X] T008 [P] Bump `waitForPptxReady` default `timeoutMs` 45_000 → 60_000 in `packages/web-dashboard/app/lib/api.ts` to cover the added research phase — Contract G.
- [X] T009 Add/extend tests in `packages/backend/tests/`: (a) `test_pptx_agent.py` — pre-session prep persists bundle+status and `pptx_ready` only true after research saved; (b) `test_content_research.py` — with Context7/Exa clients patched to raise, report-time content analysis for a session with a persisted bundle succeeds and invokes zero client calls (SC-001), plus failed-research → `skipped` still readies deck (SC-004).

---

## Dependencies

```text
T001 ─┬─▶ T003 ─▶ T005 ─▶ T006 ─▶ T007 ─▶ T009
T002 ─┘            ▲
T004 ──────────────┘ (research() consumed by persist/workflow)
T008  (independent — frontend)
```

- T001, T002 foundational (T002 [P] parallel to T001).
- T003 needs T001. T004 needs T002. T005 needs T003+T004. T006 needs T005. T007 needs T001+T002. T009 last.
- T008 [P] anytime.

## Parallel opportunities

- T002 ∥ T001 (different files).
- T008 ∥ everything (frontend, isolated).

## MVP scope

US1 (T001–T007) is the full feature: research moves to pre-session, persists, reused at report time, gated by existing `pptx_ready`. US2 resilience (FR-006/007) and US3 non-technical skip (FR-005) are satisfied inside T004/T006 — no separate phases. T008–T009 harden + validate.
