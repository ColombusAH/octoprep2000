# Implementation Plan: Hebrew & RTL Support

**Branch**: `20260624-hebrew-rtl-support` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/20260624-hebrew-rtl-support/spec.md`

**Note**: This template is filled in by the `/spec.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

> **Revision note**: this plan was revised after merging `origin/main`, which carried in the
> `001-agent-direct-persistence` feature (Constitution v2.0.0 — each agent now writes its own
> role-scoped table directly + emits a completion signal, instead of routing all writes through the
> Orchestrator) and a `suggested_fix` field added to PPTX slide findings. See research.md for the
> specific decisions that changed as a result (Decision 2 broadened, Decision 3 switched from lazy to
> eager translation).

## Summary

Presenters explicitly declare, before starting a rehearsal, which language they will speak and which
language their uploaded deck is in (Hebrew or English, independently of each other — no automatic
detection of either). The system must (1) transcribe speech accurately using the declared language as
an STT hint, and score voice delivery using a Hebrew-aware filler/disfluency lexicon when Hebrew was
declared, (2) let the user explicitly decide whether to view a session's report in Hebrew or English —
defaulting to the declared speech language — without re-recording or re-processing the session, and
(3) render the dashboard UI mirrored right-to-left when Hebrew is active. Technical approach: both
language declarations are simple fields on the existing session-creation request (no detection logic
anywhere); `ReportAgent` generates insights in the declared speech language and, in the same write,
makes one batched translation call so both languages exist on `reports.insights` from the moment the
report is created — `GET /report?lang=` is then a pure read, with no first-toggle cost and no write
outside the table's owning agent (Constitution v2.0.0, Principle II). Deterministic, template-based
insights (voice/body, and PPTX's fallback templates) are localized directly, never machine-translated.
RTL is delivered via the `dir` attribute and Tailwind's logical-property/`rtl:` variants already
available in the installed Tailwind v4, scoped first to the report view (P1) and extended to the rest
of the dashboard chrome (P3) behind a persisted interface-language cookie.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript/React via TanStack Start (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy async, agno Agent SDK (LLM orchestration), Tikal LiteLLM
  gateway (GPT-4o text + ElevenLabs Scribe v1 STT) with direct-provider fallback, TanStack Start/React,
  Tailwind CSS v4, Radix/shadcn UI primitives already in use (`Switch`, `Label`, `Separator`)
**Storage**: PostgreSQL 15 — `sessions`, `reports` tables (existing); `reports.insights` is JSONB and
  gains an internal bilingual shape, written once by `ReportAgent` (see data-model.md); two new scalar
  columns on `sessions`
**Testing**: pytest (`packages/backend/tests/`, existing pattern: `test_wav_header.py`,
  `test_report_dedup.py`, `test_ws_auth.py`, `test_pptx_agent.py`); no frontend test runner is
  configured today — frontend changes are verified manually per the Constitution's existing workflow
  requirement
**Target Platform**: Web (browser), single FastAPI process, single-region demo deployment
**Project Type**: Web application monorepo — `packages/backend` (FastAPI), `packages/web-dashboard`
  (TanStack Start), `packages/shared-types` (shared WS/API TypeScript types)
**Performance Goals**: report generation gains exactly one bounded, batched translation call on the
  existing ≤60s soft-target path (Decision 3, research.md) — no per-toggle cost; `GET /report?lang=`
  is a pure read and resolves in <2s unconditionally (SC-003, no first-request exception)
**Constraints**: must not require re-recording or re-processing the rehearsal to view the other
  language (FR-007); must preserve session isolation and existing token model (CAR-003); must keep
  status/score meaning non-color-dependent in both LTR and RTL (CAR-005); both language declarations
  are presenter-provided and trusted as-is — no verification against actual audio/slide content (spec
  Assumptions); any new agent write must follow Constitution v2.0.0 Principle II (one writer per
  role-scoped table, completion signal after commit)
**Scale/Scope**: hackathon demo scale — single presenter per session, low concurrent session count;
  no new infrastructure, queue, or service introduced

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|---|---|
| I. Demo-First Vertical Slices | PASS. US1 (explicit speech/deck language selection + accurate Hebrew STT and voice scoring) and US2 (report language toggle, defaulting to declared speech language) are P1 and independently demoable end-to-end. US3 (full dashboard RTL chrome) is P3 and explicitly deferrable without destabilizing US1/US2 or the existing English/LTR path. |
| II. Contracted Agent Boundaries (v2.0.0) | PASS. `speech_language`/`deck_language` are part of the validated `CreateSessionBody`, written directly by `create_session` — no agent or Orchestrator round-trip needed, since nothing is discovered mid-session. `AudioAgent` and `PPTXAgent` receive `speech_language`/`deck_language` as constructor/method arguments from the code that already loads the session row (`RuntimeRegistry`, `routers/upload.py`) — no new cross-agent coupling. The report's bilingual `message_en`/`message_he` are written by `ReportAgent` as part of its own single `insert_report` call — the table's sole writer, never mutated afterward by `GET /report`. This is the specific point the post-merge Principle II amendment forced a design change (research.md Decision 3) — the original lazy/cache-on-read design would have had the GET handler write to a table it doesn't own. |
| III. Session Isolation and Explicit Sharing | PASS. The report-language selection is a per-request, read-only query parameter; it does not weaken `access_token`/`share_token` checks already enforced by `require_report_access`/`require_session_owner`. A `share_token` viewer can pick their own display language without mutating the owner's stored preference. |
| IV. Resilience Before Polish | PASS, with mitigation documented. The one added LLM call (batched translation, Decision 3) sits on the existing report-generation path alongside `ContentAnalysisAgent`'s call, with the same fallback discipline: if it fails, `ReportAgent` writes `message_he = message_en` (or vice versa) with a label rather than failing the whole report. `DEMO_MODE=replay` gets a Hebrew-speech fixture variant so the demo path is rehearsable without live STT. |
| V. Native Stack, Minimal Abstractions | PASS. There is no detection logic of any kind — `speech_language`/`deck_language` are two plain fields on an existing request body. RTL uses the `dir` attribute plus Tailwind v4's built-in logical-property/`rtl:` support, already installed. One new font dependency is required (research.md Decision 5) because the current display fonts (Tektur, Chakra Petch, Space Mono, Geist) are Latin-only and have no Hebrew glyphs. |

No violations requiring an entry in Complexity Tracking.

**Post-Design Re-check** (after Phase 1 — research.md, data-model.md, contracts/, quickstart.md, and
after merging `origin/main`): all five assessments above still hold under Constitution v2.0.0. The one
substantive change from the pre-merge design is Decision 3 (lazy → eager translation), made specifically
*because* re-checking against the new Principle II surfaced a violation in the original design (a GET
handler writing to `reports`). The replacement (translate once, inside `ReportAgent`'s own write) is
simpler to reason about and removes the "first toggle" exception from SC-003 entirely — re-checking the
gate after a real architecture change produced a better design, not just a compliant one.

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
│   ├── audio_agent.py        # accept speech_language; pass as STT language hint; Hebrew filler lexicon branch (FR-013)
│   ├── report_agent.py       # build message_en/message_he for every insight; one batched translate call; single insert_report write
│   ├── content_agent.py      # prompt writes message in speech_language instead of always English
│   ├── pptx_agent.py         # prompt given deck_language context, writes in speech_language; _FACTOR_FIX_TEMPLATES + _supplement_from_metadata get Hebrew variants
│   └── schemas.py            # CreateSessionBody gains speech_language/deck_language; Insight gains message_en/message_he
├── db/
│   ├── models.py              # Session.speech_language, Session.deck_language columns
│   └── migrations/            # new Alembic revision, chained after c4f8a2b1d903_add_suggested_fix_to_slide_analyses
├── runtime.py                  # RuntimeRegistry passes speech_language into AudioAgent(...)
└── routers/
    ├── sessions.py             # create_session accepts+stores both fields; GET /report gains ?lang=en|he (pure read)
    └── upload.py                # passes speech_language/deck_language into PPTXAgent.analyse(...)

packages/shared-types/src/
└── index.ts                    # ReportData gains language, speech_language; create-session request gains both fields

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
| Business Logic | 1 | 3 | The batched eager-translation write inside `ReportAgent` touches the report contract and the ≤60s gate — human review required. Wiring `speech_language`/`deck_language` through to prompts and the STT call, the Hebrew filler-word lexicon, and the PPTX deterministic-template Hebrew variants are self-contained and agent-draftable now that no detection logic is involved. |
| Data Operations | 1 | 1 | The `sessions.speech_language`/`deck_language` migration is reviewed by a human (schema change, must chain after the upstream `suggested_fix` migration); the columns' simple defaults make the migration itself low-risk and agent-draftable. |
| UI Components | 1 | 2 | The report-view language toggle and RTL layout pass need human visual review against the Y2K dashboard aesthetic; the `start` screen's two new language controls and the Settings row are agent-suitable, well-bounded additions. |
| Integrations | 1 | 0 | Confirming the STT language-hint wiring and the translation-failure fallback behave safely under failure is human-reviewed (demo-day risk). |
| Infrastructure | 0 | 1 | Adding the Hebrew-capable font package and a Hebrew `DEMO_MODE=replay` fixture is agent-suitable. |

### Triage Decision Criteria Applied

**High-Risk [SYNC] Classifications:**

- Eager batched translation + single bilingual `insert_report` write, and its failure fallback (Principle II ownership + Principle IV resilience, demo-day risk)
- `sessions.speech_language`/`deck_language` migration review (schema change, ordering vs. upstream migration)
- Report-view RTL/visual pass (brand/aesthetic risk, no automated check)

**Agent-Delegated [ASYNC] Classifications:**

- `start` screen language controls + `CreateSessionBody` field wiring
- Hebrew filler-word lexicon + per-language branch in `audio_agent.py`
- Hebrew variants of `_FACTOR_FIX_TEMPLATES`/`_supplement_from_metadata` in `pptx_agent.py`
- Hebrew `DEMO_MODE=replay` fixture authoring, Hebrew font dependency, Settings row

### Triage Audit Trail

| Task | Classification | Primary Criteria | Risk Level | Rationale |
|------|----------------|------------------|------------|-----------|
| Add `speech_language`/`deck_language` to session creation (request, model, migration) | SYNC | Schema change/Principle II | Low–Medium | Simple, additive columns with safe defaults, but still a reviewed migration ordered after the upstream one |
| Wire `speech_language` into STT call + filler-lexicon branch | ASYNC | Self-contained, spec-mandated (FR-008, FR-013) | Low | No detection logic, no architectural risk |
| Wire `speech_language`/`deck_language` into PPTX prompt + Hebrew template variants | ASYNC | Self-contained, spec-mandated (FR-009, Decision 2) | Low | Bounded, finite content (12 templates + ~8 f-strings) |
| `ReportAgent`: build bilingual insights + one batched translate call + single write | SYNC | Resilience/Principle II/IV | Medium | Must not regress the ≤60s report-generation target, must respect table ownership, must fail safely on demo day |
| `start` screen language controls | ASYNC | Self-contained UI addition | Low | Two simple selects with safe defaults |
| RTL visual pass on report view | SYNC | Brand/UX quality | Medium | No automated check catches mirrored-layout regressions |
| Hebrew font dependency + Settings row | ASYNC | Self-contained | Low | Additive, no existing behavior at risk |

## Complexity Tracking

> No Constitution Check violations were identified; this section is intentionally empty.
