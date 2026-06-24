---
description: "Task list — Agent-Owned Persistence (minimum task set)"
---

# Tasks: Agent-Owned Persistence (Direct-to-Agent Data Flow)

**Input**: Design documents from `/specs/001-agent-direct-persistence/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Not requested. No separate test tasks; validation via `quickstart.md` + `make test`/`make lint`.

**Mode**: Minimum task set (per user request). One task per logical change.

## Format: `[ID] [P?] [SYNC/ASYNC] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependency)
- **[SYNC]**: Human review required · **[ASYNC]**: Delegable
- **[Story]**: US1–US4 from spec.md

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Governance gate + shared write primitive. MUST complete before any agent change.

- [X] T001 [SYNC] Amend Constitution Principle II in `.specify/memory/constitution.md` to permit each agent writing only its own role-scoped table(s) + emit a completion signal, keeping typed contracts, no agent-to-agent coupling, session scope, and versionable WS types (wording in `research.md` Decision 6). **Blocks all implementation (FR-013).**
- [X] T002 [ASYNC] Add `CompletionKind` literal + `CompletionSignal` model to `packages/backend/agents/schemas.py`, and revise the module docstring that asserts "Agents NEVER write to the DB directly" (per `data-model.md`).
- [X] T003 [ASYNC] Create `packages/backend/agents/persistence.py` with an `AgentPersistence` helper wrapping `get_session_maker()` + `PostgreSQLRepository` (mirror `Orchestrator._with_repo`; fresh session per write, B2 pattern) per `contracts/agent-persistence-contract.md`.

---

## Phase 2: User Story 1 — Agents persist their own live-capture results (P1)

**Goal**: Vision + Audio agents write their own rows; live feedback preserved.
**Independent test**: Replay session → `video_events`, `transcript_entries`, `audio_warnings` written by the agents (not Orchestrator); live feedback + final report match baseline (quickstart Scenario 1 + 4).

- [X] T004 [SYNC] [US1] In `packages/backend/agents/vision_agent.py`: take over `video_events` writes via the helper, move the batch buffer + 1s/N=20 flush from the Orchestrator into the agent (FR-009), publish each event to `broadcaster` directly, and call `orchestrator.notify_complete(session_id, "VIDEO", ...)` after each durable flush.
- [X] T005 [P] [SYNC] [US1] In `packages/backend/agents/audio_agent.py`: take over `transcript_entries` + `audio_warnings` writes via the helper, publish warnings to `broadcaster` directly, and call `orchestrator.notify_complete(session_id, "AUDIO")` after commit.

---

## Phase 3: User Story 2 — Completion signals + Orchestrator reads the agreed place (P1)

**Goal**: Orchestrator stops writing live data, coordinates via completion signals, ensures durability before report read.
**Independent test**: End session → final vision flush precedes report read; report assembled purely from DB; session → REPORT_READY (quickstart Scenario 2).

- [X] T006 [SYNC] [US2] In `packages/backend/orchestrator/orchestrator.py`: remove the write bodies of `on_video_event`/`on_transcript`/`on_audio_warning`/`on_slide_analysis`/`on_report` (drop `_video_buffer`/`_flush_task`); add `notify_complete(session_id, kind, meta)` + `_completion` state + `completed()`; keep `start_session`/`end_session`/`set_session_status`, fallback, and `REPORT_READY`/`FALLBACK_ACTIVATED` broadcasts. In `end_session`, await the VisionAgent final flush before report read.
- [X] T007 [SYNC] [US2] In `packages/backend/routers/sessions.py` + `packages/backend/agents/report_agent.py`: ReportAgent now writes its own report via the helper (`insert_report`) and calls `notify_complete(session_id, "REPORT")`; update the `POST /sessions/:id/end` flow so it no longer calls `Orchestrator.on_report` for the write (it already reads the DB to build the payload).

---

## Phase 4: User Story 3 — PPTX persisted by its owning agent (P2)

**Goal**: PPTXAgent owns its writes.
**Independent test**: Upload deck → agent writes `slides_raw_text` (before LLM) then `slide_analyses`, signals PPTX; `GET /sessions/:id` shows `pptx_ready=true` (quickstart Scenario 3).

- [X] T008 [P] [SYNC] [US3] In `packages/backend/agents/pptx_agent.py`: take over `mark_pptx_ready` (raw text first, §10b.6 ordering) + `insert_slide_analyses` writes via the helper, and call `orchestrator.notify_complete(session_id, "PPTX")` after both commit. Remove the `Orchestrator.on_slide_analysis` write dependency.

---

## Phase 5: User Story 4 — Docs + presentation reflect new flow (P2)

**Goal**: Architecture docs + kickoff deck match implementation.
**Independent test**: `grep -ri "sole writer" docs/` returns nothing describing the live flow; sequence/diagrams show direct-to-agent writes + completion signals (quickstart Scenario 6, SC-007).

- [X] T009 [P] [ASYNC] [US4] Update `docs/TECH-ARCHITECTURE-C4.md` (component §3, sequence §4 flows, any "Orchestrator is sole writer" statements) and any data-flow lines in `docs/PRD.md` / `docs/MASTER-DOCUMENT.md` to describe agent-owned writes + completion signals + Orchestrator reading the agreed tables.
- [X] T010 [P] [ASYNC] [US4] Update the architecture slide(s) diagram + narration in `docs/presentation/ARCHITECTURE-DECK.html` to match the new flow.

---

## Phase 6: Polish & Validation

- [X] T011 [SYNC] Run `quickstart.md` Scenarios 1–6 (incl. `DEMO_MODE=replay` run, baseline equivalence, Vision-timeout fallback), then `make test` and `make lint`; confirm no report regression and one-writer-per-table invariant holds.

---

## Dependencies

- **T001 blocks everything** (governance gate).
- **T002, T003 block all agent tasks** (shared model + helper). T002 ∥ T003.
- US1 (T004, T005) and US3 (T008) depend on T002/T003; T004 ∥ T005 ∥ T008 (different files).
- **T006 (US2) depends on T004** (batching/flush moved into VisionAgent before Orchestrator drops it).
- T007 (US2) depends on T002/T003; can follow T006.
- US4 (T009, T010) independent of code once behavior is settled; best done after T006/T008. T009 ∥ T010.
- T011 last (validates all).

## Parallel Opportunities

- After T001 → T002 ∥ T003.
- After foundation → T004 ∥ T005 ∥ T008.
- Docs phase → T009 ∥ T010.

## Implementation Strategy

- **MVP = US1 (T001→T003→T004/T005)**: agents own the high-volume live writes — the core of the requested change, independently demoable in replay mode.
- Then US2 (orchestrator slimming + report-write move) completes the inversion; US3 brings PPTX into line; US4 syncs docs/presentation; T011 validates.
