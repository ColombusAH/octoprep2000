# Phase 1 Data Model: Agent-Owned Persistence

**Feature**: 001-agent-direct-persistence
**Date**: 2026-06-24

> No database schema changes. Existing tables become the explicit shared read/write contract
> ("the agreed place"). This document records ownership, not new structure.

## Persistence ownership (the change)

| Table / column | Producer (writer) — NEW owner | Reader | Was written by (OLD) |
|---|---|---|---|
| `video_events` | **VisionAgent** (batched: N=20 or 1s) | ReportAgent | Orchestrator.on_video_event |
| `transcript_entries` | **AudioAgent** | ReportAgent, ContentAnalysisAgent | Orchestrator.on_transcript |
| `audio_warnings` | **AudioAgent** | ReportAgent | Orchestrator.on_audio_warning |
| `slide_analyses` | **PPTXAgent** | ReportAgent | Orchestrator.on_slide_analysis |
| `sessions.slides_raw_text`, `sessions.pptx_ready` | **PPTXAgent** (`mark_pptx_ready`) | GET /sessions/:id, ContentAgent | Orchestrator.on_slide_analysis |
| `reports` | **ReportAgent** (`insert_report`) | GET /sessions/:id/report | Orchestrator.on_report |
| `sessions.status` (ACTIVE→ENDED→REPORT_READY) | **Orchestrator** (unchanged) | routers | Orchestrator |

**Entities themselves are unchanged** — see `packages/backend/db/models.py`. Fields, types,
relationships, indexes, and cascade rules stay exactly as today.

## New in-memory contract object: CompletionSignal

Not persisted. Carries the "I finished" notification from an agent to the Orchestrator.

| Field | Type | Notes |
|---|---|---|
| `session_id` | UUID | Scopes the signal to one session |
| `kind` | `CompletionKind` = Literal["VIDEO","AUDIO","PPTX","CONTENT","REPORT"] | Which agent role completed a unit |
| `meta` | dict \| None | Optional (e.g. `{"events_flushed": 12}`) for logs/tests |

**Validation rules**:
- `session_id` MUST reference an existing session the caller is authorized for.
- `kind` MUST be one of the allowed literals (Pydantic-enforced).
- A signal is emitted only **after** the corresponding write has committed (durability before
  notify — see contracts/completion-signal.md).

## Orchestrator in-memory completion state

| Structure | Type | Purpose |
|---|---|---|
| `_completion` | `dict[UUID, set[CompletionKind]]` | Tracks which kinds have signaled per session |
| `_video_buffer` | (removed — moves to VisionAgent) | — |
| `_flush_task` | (removed — moves to VisionAgent) | — |
| `_fallback_active` | `set[UUID]` | Unchanged |
| `_tasks` | `dict[UUID, dict[str, Task]]` | Unchanged |

## State transitions (unchanged externally)

```
ACTIVE ──POST /sessions/:id/end──▶ ENDED ──report persisted──▶ REPORT_READY
```

The transition owner stays the Orchestrator. What changes: at `end`, the Orchestrator ensures the
VisionAgent has flushed its final batch (durability) before ReportAgent reads `video_events`.

## Pydantic payloads (`agents/schemas.py`)

- Existing payloads (`VideoEventPayload`, `TranscriptPayload`, `AudioWarningPayload`,
  `SlideAnalysisBundle`, `ReportPayload`, `FeedbackEvent`) are **retained** — still the typed,
  validated shapes agents build before writing. The validation wall moves from
  "Orchestrator.on_* validates then writes" to "agent validates (constructs payload) then writes".
- **Add** `CompletionSignal` + `CompletionKind` literal.
- Update the module docstring: it currently asserts "Agents NEVER write to the DB directly" — that
  statement is reversed by this feature (see contracts/agent-persistence-contract.md).
