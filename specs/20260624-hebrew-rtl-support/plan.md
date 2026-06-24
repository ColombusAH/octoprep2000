# Implementation Plan: Hebrew & RTL Support

**Branch**: `20260624-hebrew-rtl-support` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/20260624-hebrew-rtl-support/spec.md`

**Note**: This template is filled in by the `/spec.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Presenters explicitly declare, before starting a rehearsal, which language they will speak and which
language their uploaded deck is in (Hebrew or English, independently of each other — no automatic
detection of either). The system must (1) transcribe speech accurately using the declared language as
an STT hint, and score voice delivery using a Hebrew-aware filler/disfluency lexicon when Hebrew was
declared, (2) let the user explicitly decide whether to view a session's report in Hebrew or English —
defaulting to the declared speech language — without re-recording or re-processing the session, and
(3) render the dashboard UI mirrored right-to-left when Hebrew is active. Technical approach: both
language declarations are simple fields on the existing session-creation request (no detection logic
anywhere); insight generation on the critical report-generation path is unchanged in cost (single LLM
call per agent, now explicitly prompted to write in the declared speech language); the non-default
language is resolved lazily — translated once on first request and cached in the existing
`reports.insights` JSONB column. RTL is delivered via the `dir` attribute and Tailwind's
logical-property/`rtl:` variants already available in the installed Tailwind v4, scoped first to the
report view (P1) and extended to the rest of the dashboard chrome (P3) behind a persisted
interface-language cookie.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript/React via TanStack Start (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy async, agno Agent SDK (LLM orchestration), Tikal LiteLLM
  gateway (GPT-4o text + ElevenLabs Scribe v1 STT) with direct-provider fallback, TanStack Start/React,
  Tailwind CSS v4, Radix/shadcn UI primitives already in use (`Switch`, `Label`, `Separator`)
**Storage**: PostgreSQL 15 — `sessions`, `reports` tables (existing); `reports.insights` is JSONB and
  gains an internal bilingual shape (see data-model.md); two new scalar columns on `sessions`
**Testing**: pytest (`packages/backend/tests/`, existing pattern: `test_wav_header.py`,
  `test_report_dedup.py`, `test_ws_auth.py`); no frontend test runner is configured today — frontend
  changes are verified manually per the Constitution's existing workflow requirement
**Target Platform**: Web (browser), single FastAPI process, single-region demo deployment
**Project Type**: Web application monorepo — `packages/backend` (FastAPI), `packages/web-dashboard`
  (TanStack Start), `packages/shared-types` (shared WS/API TypeScript types)
**Performance Goals**: report generation stays inside the existing ≤60s soft target (no new LLM call
  added to that path); language toggle resolves in <2s once a language has been resolved once per
  report (first toggle into the non-default language pays one short, cached translation call — see
  research.md Decision 3)
**Constraints**: must not require re-recording or re-processing the rehearsal to view the other
  language (FR-007); must preserve session isolation and existing token model (CAR-003); must keep
  status/score meaning non-color-dependent in both LTR and RTL (CAR-005); both language declarations
  are presenter-provided and trusted as-is — no verification against actual audio/slide content
  (spec Assumptions)
**Scale/Scope**: hackathon demo scale — single presenter per session, low concurrent session count;
  no new infrastructure, queue, or service introduced

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|---|---|
| I. Demo-First Vertical Slices | PASS. US1 (explicit speech/deck language selection + accurate Hebrew STT and voice scoring) and US2 (report language toggle, defaulting to declared speech language) are P1 and independently demoable end-to-end. US3 (full dashboard RTL chrome) is P3 and explicitly deferrable without destabilizing US1/US2 or the existing English/LTR path. |
| II. Contracted Agent Boundaries | PASS. `speech_language`/`deck_language` are part of the validated `CreateSessionBody` and are written directly by `create_session` — no agent payload or Orchestrator round-trip is needed for this part at all, since nothing is discovered mid-session anymore. `AudioAgent` receives `speech_language` as a constructor argument from `RuntimeRegistry` (which already owns session lookup), not via a new cross-agent dependency. |
| III. Session Isolation and Explicit Sharing | PASS. The report-language selection is a per-request, read-only query parameter; it does not weaken `access_token`/`share_token` checks already enforced by `require_report_access`/`require_session_owner`. A `share_token` viewer can pick their own display language without mutating the owner's stored preference. |
| IV. Resilience Before Polish | PASS, with mitigation documented. Lazy/cached translation (Decision 3, research.md) keeps the new work off the critical report-generation path so the existing ≤60s target is not put at additional risk. If the on-demand translation call fails, the system MUST fall back to the original-language text with a label (same graceful-degradation pattern already used for Vision/STT fallback) rather than blocking the toggle. `DEMO_MODE=replay` gets a Hebrew-speech fixture variant so the demo path is rehearsable without live STT. |
| V. Native Stack, Minimal Abstractions | PASS, and simpler than the previous draft of this plan. There is no detection logic of any kind — `speech_language`/`deck_language` are two plain fields on an existing request body. RTL uses the `dir` attribute plus Tailwind v4's built-in logical-property/`rtl:` support, already installed. One new font dependency is required (research.md Decision 5) because the current display fonts (Tektur, Chakra Petch, Space Mono, Geist) are Latin-only and have no Hebrew glyphs — this is a concrete constraint, not a speculative addition. |

No violations requiring an entry in Complexity Tracking.

**Post-Design Re-check** (after Phase 1 — research.md, data-model.md, contracts/, quickstart.md):
all five assessments above still hold, and the explicit-selection redesign (replacing an earlier
Unicode-detection draft of Decision 1) made Principle V's PASS stronger, not weaker — there is now
zero inference logic anywhere in the spoken/deck-language path. The lazy-translate-and-cache approach
(Decision 3) still keeps new LLM latency off the ≤60s report-generation path, and now additionally
benefits from knowing `speech_language` *before* the session starts, so the first (free) LLM-generated
language is correct by construction rather than detected after the fact.

## Project Structure

### Documentation (this feature)

```text
specs/20260624-hebrew-rtl-support/
├── plan.md              # This file (/spec.plan command output)
├── research.md          # Phase 0 output (/spec.plan command)
├── data-model.md        # Phase 1 output (/spec.plan command)
├── quickstart.md        # Phase 1 output (/spec.plan command)
├── contracts/           # Phase 1 output (/spec.plan command)
│   └── report-api.md     # POST /sessions + GET /sessions/{id}/report contract changes
└── tasks.md             # Phase 2 output (/spec.tasks command - NOT created by /spec.plan)
```

### Source Code (repository root)

```text
packages/backend/
├── agents/
│   ├── audio_agent.py        # accept speech_language; pass as STT language hint; branch filler lexicon (FR-013)
│   ├── report_agent.py       # bilingual deterministic templates; lazy-translate LLM-derived insights
│   ├── content_agent.py      # prompt now writes in speech_language instead of always English
│   ├── pptx_agent.py         # prompt given deck_language context; writes findings in speech_language
│   └── schemas.py            # CreateSessionBody gains speech_language/deck_language; Insight gains lang fields
├── db/
│   ├── models.py              # Session.speech_language, Session.deck_language columns
│   └── migrations/            # new Alembic revision for the two columns above
├── runtime.py                  # RuntimeRegistry passes speech_language into AudioAgent(...)
└── routers/
    ├── sessions.py             # create_session accepts+stores both fields; GET /report gains ?lang=en|he
    └── (CreateSessionBody/CreateSessionResponse already routed through sessions.py)

packages/shared-types/src/
└── index.ts                    # ReportData gains language, speech_language; CreateSessionRequest-equivalent gains both fields

packages/web-dashboard/app/
├── routes/
│   ├── start.tsx                 # two new controls: speech language, deck language (default English)
│   ├── session.$id_.report.tsx   # language toggle control, dir="rtl" scoped to report view (P1)
│   ├── settings.tsx              # interface-language preference row (P3, FR-011)
│   └── __root.tsx                 # read persisted UI-language cookie, set <html lang dir> on SSR (P3)
├── lib/
│   └── api.ts                     # createSession({..., speech_language, deck_language}); getReport(id, share, lang?)
└── components/
    └── ScoreCard.tsx               # RTL-aware layout for score/insight rendering
```

**Structure Decision**: Existing monorepo layout is reused as-is (`packages/backend`,
`packages/web-dashboard`, `packages/shared-types`); no new package, service, or directory is
introduced, per Constitution Principle V.

## Triage Framework: [SYNC] vs [ASYNC] Classification

**Execution Strategy**: This feature will use a hybrid execution model combining human expertise ([SYNC]) with autonomous agent delegation ([ASYNC]).

### Preliminary Task Classification

| Task Category | Estimated [SYNC] Tasks | Estimated [ASYNC] Tasks | Rationale |
|---------------|----------------------|----------------------|-----------|
| Business Logic | 1 | 2 | Lazy-translation/caching logic touches the report contract and the ≤60s constitutional gate — human review required. Wiring `speech_language`/`deck_language` through to prompts and the STT call, and the Hebrew filler-word lexicon, are self-contained and agent-draftable now that no detection logic is involved. |
| Data Operations | 1 | 1 | The `sessions.speech_language`/`deck_language` migration is reviewed by a human (schema change); the columns' simple defaults make the migration itself low-risk and agent-draftable. |
| UI Components | 1 | 2 | The report-view language toggle and RTL layout pass need human visual review against the Y2K dashboard aesthetic; the `start` screen's two new language controls and the Settings row are agent-suitable, well-bounded additions. |
| Integrations | 1 | 0 | Confirming the STT language-hint wiring and translation fallback behave safely under failure is human-reviewed (demo-day risk). |
| Infrastructure | 0 | 1 | Adding the Hebrew-capable font package and a Hebrew `DEMO_MODE=replay` fixture is agent-suitable. |

### Triage Decision Criteria Applied

**High-Risk [SYNC] Classifications:**

- Lazy-translation caching and its failure fallback (Principle IV, demo-day risk)
- `sessions.speech_language`/`deck_language` migration review (schema change)
- Report-view RTL/visual pass (brand/aesthetic risk, no automated check)

**Agent-Delegated [ASYNC] Classifications:**

- `start` screen language controls + `CreateSessionBody` field wiring
- Hebrew filler-word lexicon + per-language branch in `audio_agent.py`
- Hebrew `DEMO_MODE=replay` fixture authoring, Hebrew font dependency, Settings row

### Triage Audit Trail

| Task | Classification | Primary Criteria | Risk Level | Rationale |
|------|----------------|------------------|------------|-----------|
| Add `speech_language`/`deck_language` to session creation (request, model, migration) | SYNC | Schema change/Principle II | Low–Medium | Simple, additive columns with safe defaults, but still a reviewed migration |
| Wire `speech_language` into STT call + filler-lexicon branch | ASYNC | Self-contained, spec-mandated (FR-008, FR-013) | Low | No detection logic, no architectural risk |
| Lazy-translate + cache non-default-language insights | SYNC | Resilience/Principle IV | Medium | Must not regress the ≤60s report-generation target or fail unsafely on demo day |
| `start` screen language controls | ASYNC | Self-contained UI addition | Low | Two simple selects with safe defaults |
| RTL visual pass on report view | SYNC | Brand/UX quality | Medium | No automated check catches mirrored-layout regressions |
| Hebrew font dependency + Settings row | ASYNC | Self-contained | Low | Additive, no existing behavior at risk |

## Complexity Tracking

> No Constitution Check violations were identified; this section is intentionally empty.
