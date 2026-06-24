# Implementation Plan: Pre-Session Topic Research Persistence

**Branch**: `main` (no feature branch — `git.feature` hook disabled) | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-pre-session-research/spec.md`

## Summary

Move the existing Context7 + Exa topic research out of the post-session `ContentAnalysisAgent` and into the pre-session `PptxPrepWorkflow`. Add a `research` step to that workflow; the `PPTXAgent` classifies the topic, fetches the `ReferenceBundle` (reusing the unchanged `content_research/` module), and persists the bundle + a research status onto the session row in the same write step that marks the deck ready. Because the existing session-start gate polls `sessions.pptx_ready` — which only flips true in that final write step — placing research before the write makes session start automatically wait for research, with no new gating logic. At report time, `ContentAnalysisAgent` reads the persisted bundle and status instead of calling any provider.

## Technical Context

**Language/Version**: Python 3.11+ (backend); TypeScript (one frontend timeout touch-up)
**Primary Dependencies**: FastAPI, Agno Workflow, SQLAlchemy async, existing `content_research/` module (`classifier`, `fetcher`, `context7_client`, `exa_client`, `reference_bundle`). No new dependencies.
**Storage**: PostgreSQL — add two nullable columns to `sessions` (`research_bundle` JSONB, `content_research_status` String(32)), mirroring the existing `slides_raw_text` JSONB pattern. No new table.
**Testing**: pytest + pytest-asyncio; reuse existing stubs for Context7/Exa; new tests for pre-session research persistence + report-time read path.
**Target Platform**: Single FastAPI process (local + Railway)
**Project Type**: Web app (Python backend + TanStack Start frontend, monorepo)
**Performance Goals**: Pre-session research ≤20s (existing `content_research_timeout_s`); report generation no longer includes any research wait (target ≥10s saved at session end); deck-ready signal still returns within the frontend poll window.
**Constraints**: Constitution I (demo path), II (agent-owned writes), IV (resilience), V (minimal stack). Research must be timeout-bounded so `mark_pptx_ready` always runs. Demo replay bypasses research.
**Scale/Scope**: 1 research fetch per session at pre-session time; 2–4 external calls max; bundle capped at ~14k chars (`MAX_TOTAL_CHARS`, unchanged).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Gate | Status | Notes |
|---|---|---|
| **I. Demo-First Vertical Slices** | ✅ PASS | Core path preserved: upload → (prep now includes research) → rehearse → end → report. Research failure degrades; report still renders. |
| **II. Contracted Agent Boundaries** | ✅ PASS | `PPTXAgent` already owns `sessions` writes (`mark_pptx_ready`, `slides_raw_text`); it now also writes the two new session columns in the same role-scoped write. `ContentAnalysisAgent` reads them (narrow scoped read). No new writer for an existing table; `reports.content_research_status` still written by `ReportAgent`. |
| **III. Session Isolation** | ✅ PASS | Research read/write keyed to owning `session_id`; upload already behind `require_session_owner`. No new cross-session path. |
| **IV. Resilience Before Polish** | ✅ PASS | `fetch_reference_bundle` keeps per-provider timeout + partial fallback; research step wrapped so failure never blocks `mark_pptx_ready`. `DEMO_MODE=replay` bypasses research. Report-time missing-bundle → transcript-only. |
| **V. Native Stack, Minimal Abstractions** | ✅ PASS | No new dependency. JSONB column reuses the `slides_raw_text` pattern rather than a new table. agno Workflow step added as pure glue (`telemetry=False, db=None`). |

**Post-design re-check**: All gates pass. No constitution amendment required. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-pre-session-research/
├── plan.md              # This file
├── research.md          # Phase 0 decisions
├── data-model.md        # Phase 1 entities
├── quickstart.md        # Phase 1 validation guide
├── contracts/
│   └── session-research.md
├── checklists/
│   └── requirements.md  # from /spec-specify
└── tasks.md             # Phase 2 (/spec-tasks — not yet created)
```

### Source Code (repository root)

```text
packages/backend/
├── agents/
│   ├── pptx_agent.py                 # + research() phase; persist research_bundle + status on session
│   ├── content_agent.py              # read persisted bundle/status; NO classify/fetch at report time
│   ├── content_research/             # UNCHANGED (classifier, fetcher, *_client, reference_bundle)
│   │   └── reference_bundle.py       # + (de)serialize helpers for JSONB persistence
│   └── replay_fixtures.py            # research bypass under demo replay (reuse existing)
├── workflows/
│   └── pptx_prep.py                  # + research step before write (extract → review → research → write)
├── db/
│   ├── models.py                     # Session: + research_bundle (JSONB), + content_research_status (String)
│   └── repository.py                 # mark_pptx_ready persists research; getter for persisted bundle
├── migrations/versions/
│   └── <new>_add_session_research.py # add 2 columns to sessions (down_revision a1b2c3d4e5f6)
└── tests/
    ├── test_pptx_agent.py            # + pre-session research persistence
    └── test_content_research.py      # + report-time read path (no live calls)

packages/web-dashboard/
└── app/lib/api.ts                    # bump waitForPptxReady timeout to cover research (~60s)
```

**Structure Decision**: Monorepo unchanged. Research logic stays in the existing `content_research/` package (no rewrite); only its call site moves from `ContentAnalysisAgent` to `PPTXAgent`, and a serialization helper is added to `reference_bundle.py`. Persistence reuses the `sessions` row the PPTX agent already owns.

## Triage Framework: [SYNC] vs [ASYNC] Classification

**Execution Strategy**: Hybrid — schema/contract and gating-order changes reviewed by a human ([SYNC]); mechanical wiring and tests delegable ([ASYNC]).

### Preliminary Task Classification

| Task Category | Estimated [SYNC] Tasks | Estimated [ASYNC] Tasks | Rationale |
|---------------|----------------------|----------------------|-----------|
| Business Logic | 2 | 1 | Research-before-write ordering + report-time read path are correctness-critical (SYNC); bundle (de)serialize helper is mechanical (ASYNC). |
| Data Operations | 1 | 1 | Migration + model columns reviewed (SYNC); repository getter/setter wiring (ASYNC). |
| UI Components | 0 | 1 | Only a frontend poll-timeout bump (ASYNC). |
| Integrations | 1 | 0 | Adding the research step into PptxPrepWorkflow with resilience wrapping (SYNC). |
| Infrastructure | 0 | 0 | No new infra. |

### Triage Decision Criteria Applied

**High-Risk [SYNC] Classifications:**

- Ordering research before `mark_pptx_ready` so the existing `pptx_ready` gate enforces FR-006 — wrong order breaks the gating guarantee.
- Resilience wrapping of the research step (FR-007): failure/timeout must still let the write step run.
- Report-time read path proving zero provider calls (FR-004 / SC-001).
- DB migration + model column addition (data contract).

**Agent-Delegated [ASYNC] Classifications:**

- `ReferenceBundle` ↔ JSONB (de)serialization helper.
- Repository read/write plumbing for the new columns.
- Frontend `waitForPptxReady` timeout bump.
- Test scaffolding reusing existing Context7/Exa stubs.

### Triage Audit Trail

| Task | Classification | Primary Criteria | Risk Level | Rationale |
|------|----------------|------------------|------------|-----------|
| Add research step + ordering in PptxPrepWorkflow | SYNC | Demo-path / gating correctness | High | Enforces FR-006 via existing gate; must precede write. |
| Resilience-wrap research step | SYNC | Resilience (IV) | High | Must never block mark_pptx_ready. |
| ContentAgent reads persisted bundle, no live fetch | SYNC | Contract / SC-001 | Med | Core behavioural change. |
| DB migration + Session columns | SYNC | Data contract | Med | Schema change reviewed once. |
| Bundle (de)serialize helper | ASYNC | Mechanical | Low | Pure transform with tests. |
| Repository getter/setter wiring | ASYNC | Mechanical | Low | Mirrors mark_pptx_ready. |
| Frontend poll timeout bump | ASYNC | UI copy/config | Low | Single constant. |

## Complexity Tracking

> No constitution violations. Section intentionally empty.
