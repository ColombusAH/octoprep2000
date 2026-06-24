# Implementation Plan: Agent-Owned Persistence (Direct-to-Agent Data Flow)

**Branch**: `main` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-agent-direct-persistence/spec.md`

## Summary

Move database-write ownership out of the Orchestrator and into each role-owning agent. Today the
Orchestrator is the sole writer: agents emit typed payloads via `on_video_event` / `on_transcript`
/ `on_audio_warning` / `on_slide_analysis` / `on_report`, and the Orchestrator persists them. After
this change, each agent writes its own role-scoped rows to the existing Postgres tables ("the agreed
place"), emits a completion signal, and the Orchestrator coordinates lifecycle + assembles the
report by reading those tables (which the ReportAgent already does). Video-event batching moves to
the VisionAgent. No schema change, no new infrastructure. Docs and the kickoff architecture
presentation are updated to match. The change conflicts with Constitution Principle II and is gated
on a constitution amendment.

## Technical Context

**Language/Version**: Python 3.11+ (backend); TypeScript/React (frontend, untouched)
**Primary Dependencies**: FastAPI, SQLAlchemy async, Pydantic, loguru, Agno (agent runtime),
asyncio; TanStack Start (frontend)
**Storage**: PostgreSQL 15 — existing tables (`sessions`, `video_events`, `transcript_entries`,
`audio_warnings`, `slide_analyses`, `reports`). No migration.
**Testing**: pytest (`make test`); ruff (`make lint`)
**Target Platform**: Single-process FastAPI server (port 8000), Postgres in Docker
**Project Type**: Monorepo web app (pnpm workspaces + uv); change is backend-only
**Performance Goals**: Preserve §10b.5 video batching (flush 1s / N=20); no live-feedback latency
regression beyond the existing batch window
**Constraints**: Single-process, no new infra (Principle V); `DEMO_MODE=replay` must stay green;
audio-only fallback + score reweighting preserved; demo path equivalence (FR-011)
**Scale/Scope**: Backend agents + orchestrator (~6 files) + 2 docs + 1 presentation; hackathon scope

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Demo-First Vertical Slices | PASS | Core demo path preserved; equivalence required (FR-011, SC-003). Work sliced P1→P4. |
| II. Contracted Agent Boundaries | **FAIL → requires amendment** | Principle currently mandates "Orchestrator MUST own all writes … Agents MUST NOT bypass". This feature deliberately reverses that. Resolution: amend Principle II (research Decision 6, FR-013) **before** implementation. Justified in Complexity Tracking. |
| III. Session Isolation & Explicit Sharing | PASS | Ingress auth unchanged; every agent write/notify is session-scoped (CAR-003). No token logging. |
| IV. Resilience Before Polish | PASS | Batching moves intact; fallback, replay, bounded-wait-before-report, graceful degradation preserved (FR-010, CAR-004). |
| V. Native Stack, Minimal Abstractions | PASS | No new store/queue/broker; reuses repository + `get_session_maker`; completion signal is an in-process method call. |

**Gate result**: One violation (II), explicitly justified and routed to a pre-implementation
amendment. All other gates pass. Proceed to design; implementation is blocked until the amendment
lands.

## Project Structure

### Documentation (this feature)

```text
specs/001-agent-direct-persistence/
├── plan.md              # This file
├── spec.md              # Feature spec
├── research.md          # Phase 0 — 6 decisions
├── data-model.md        # Phase 1 — ownership table + CompletionSignal
├── quickstart.md        # Phase 1 — 6 validation scenarios
├── contracts/
│   ├── agent-persistence-contract.md
│   └── completion-signal.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
packages/backend/
├── agents/
│   ├── schemas.py          # +CompletionSignal/CompletionKind; revise "agents NEVER write" docstring
│   ├── persistence.py      # NEW — AgentPersistence helper (_with_repo via get_session_maker)
│   ├── vision_agent.py     # take over video_events writes + batching + broadcaster publish
│   ├── audio_agent.py      # take over transcript + audio_warning writes + broadcaster publish
│   ├── pptx_agent.py       # take over slide_analyses + mark_pptx_ready writes
│   ├── report_agent.py     # take over insert_report write
│   └── content_agent.py    # optional CONTENT completion signal (read-only otherwise)
├── orchestrator/
│   └── orchestrator.py     # remove write bodies; add notify_complete + _completion; keep lifecycle/fallback/broadcasts
├── routers/
│   ├── sessions.py         # end flow: await final vision flush before report read; report write now in agent
│   └── upload.py           # unchanged ingress; PPTXAgent now persists
└── db/
    └── repository.py       # unchanged methods; now called by agents

docs/
├── TECH-ARCHITECTURE-C4.md           # update §3 components, §4 sequences, sole-writer statements
├── PRD.md / MASTER-DOCUMENT.md       # update any data-flow description
└── presentation/ARCHITECTURE-DECK.html  # update architecture diagram + narration

.specify/memory/constitution.md       # amend Principle II (governance gate, FR-013)
```

**Structure Decision**: Backend-only change within the existing monorepo layout. No new packages,
modules limited to one new helper (`agents/persistence.py`) plus edits to existing agents,
orchestrator, two routers, schemas. Frontend and DB schema untouched.

## Triage Framework: [SYNC] vs [ASYNC] Classification

**Execution Strategy**: Hybrid — human-reviewed for the hot-path write/race changes and governance;
agent-delegated for mechanical edits and doc/presentation updates.

### Preliminary Task Classification

| Task Category | Estimated [SYNC] Tasks | Estimated [ASYNC] Tasks | Rationale |
|---------------|----------------------|----------------------|-----------|
| Business Logic | 4 | 1 | Write-ownership + batching move + completion signal are correctness-critical; report write move is mechanical. |
| Data Operations | 1 | 0 | No schema change; verify one-writer-per-table invariant (review). |
| UI Components | 0 | 0 | No UI change. |
| Integrations | 2 | 0 | Broadcaster publish relocation + end-flow ordering touch live + fallback paths. |
| Infrastructure | 1 | 1 | New `persistence.py` helper (review); doc/presentation updates (delegate). |
| Governance | 1 | 0 | Constitution Principle II amendment — human decision. |

### Triage Decision Criteria Applied

**High-Risk [SYNC] Classifications:**
- Constitution Principle II amendment (governance, blocks everything).
- VisionAgent batching + final-flush-before-report ordering (race/durability risk).
- Broadcaster publish relocation (live-feedback regression risk).
- Orchestrator write-body removal without breaking lifecycle/fallback.

**Agent-Delegated [ASYNC] Classifications:**
- `agents/persistence.py` scaffolding from the agreed pattern.
- ReportAgent `insert_report` move (mechanical).
- Docs + presentation rewrite to match new flow (text edits, grep-verified).

### Triage Audit Trail

| Task | Classification | Primary Criteria | Risk Level | Rationale |
|------|----------------|------------------|------------|-----------|
| Amend Principle II | SYNC | Governance gate | High | Unblocks implementation; standing-architecture decision. |
| VisionAgent write+batch+flush | SYNC | Live hot path, durability | High | Must preserve §10b.5 + flush-before-report. |
| AudioAgent writes+publish | SYNC | Live hot path | Med | Two tables + broadcaster, session-scoped. |
| PPTXAgent writes | SYNC | Ordering (raw text before LLM) | Med | Preserve §10b.6 crash-survival ordering. |
| Orchestrator slimming + notify_complete | SYNC | Coordination correctness | Med | Keep lifecycle/fallback; add completion state. |
| ReportAgent insert_report move | ASYNC | Mechanical write move | Low | Already reads DB; add one write + signal. |
| `agents/persistence.py` | ASYNC | Reuse known pattern | Low | Mirror Orchestrator `_with_repo`. |
| Docs + ARCHITECTURE-DECK update | ASYNC | Text accuracy | Low | Grep-gated (SC-007). |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution Principle II reversed (agents write their own rows) | The user-requested architecture requires agents to "process and put it on the DB and notify". The Orchestrator-as-sole-writer rule directly forbids this. | Keeping the Orchestrator as sole writer = not doing the feature. Resolved by amending Principle II to "one writer per role-scoped table + completion signal", preserving the rest of the boundary (typed contracts, no agent-to-agent coupling, session scope, versionable WS types). |

## Post-Design Constitution Re-check

After Phase 1 design, gates II remains the only flagged item and is fully contained by the amendment
task + the "one writer per table / durability-before-notify / session-scoped" invariants in
`contracts/`. No new violations introduced by the design. Principles I, III, IV, V hold.
