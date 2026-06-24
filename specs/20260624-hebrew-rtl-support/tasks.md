# Tasks: Hebrew & RTL Support

**Input**: Design documents from `/specs/20260624-hebrew-rtl-support/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/report-api.md, quickstart.md

**Tests**: Included, but kept minimal — only where the Constitution's testing gate ("Backend changes
to routes, payloads, data models, scoring, or agent orchestration MUST include automated tests")
actually applies. Frontend verification is manual per the Constitution's existing workflow requirement.

**Organization**: Tasks are grouped by user story (spec.md priorities) so each story is independently
implementable, testable, and demoable.

## Format: `[ID] [P?] [SYNC/ASYNC] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[SYNC]**: Requires human review (touches the report-generation critical path, a schema migration, or visual/brand quality)
- **[ASYNC]**: Self-contained, well-bounded, agent-delegable
- **[Story]**: US1, US2, or US3 — maps to spec.md's user stories

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Both language declarations must exist on the session before any story can use them.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T001 [SYNC] Add `speech_language`/`deck_language` (`Literal["en","he"]`, default `"en"`) to the `Session` model and a new Alembic migration chained after `c4f8a2b1d903_add_suggested_fix_to_slide_analyses`; add the same two fields (same defaults) to `CreateSessionBody`; wire `create_session` to persist both directly — no agent/Orchestrator round-trip needed. Files: `packages/backend/db/models.py`, `packages/backend/db/migrations/versions/<new>.py`, `packages/backend/agents/schemas.py`, `packages/backend/routers/sessions.py`.

**Checkpoint**: Foundation ready — User Stories 1, 2, and 3 can now proceed.

---

## Phase 2: User Story 1 - Declare speech and deck language, then rehearse in Hebrew (Priority: P1) 🎯 MVP

**Goal**: A presenter explicitly picks their speech language and deck language before rehearsing, and gets an accurate Hebrew transcript with accurate Hebrew-aware voice coaching (not silently-English-biased).

**Independent Test**: Start a session with speech language = Hebrew, deck language = English, upload an English deck, speak Hebrew (including a Hebrew filler word), end the session, and confirm the stored transcript and filler-count insight are both correct.

- [X] T002 [P] [ASYNC] [US1] Add two select controls to the start screen — "Speech language" and "Deck language" (Hebrew/English, both default English) — and send them in the `createSession(...)` call body. Files: `packages/web-dashboard/app/routes/start.tsx`, `packages/web-dashboard/app/lib/api.ts`.
- [X] T003 [ASYNC] [US1] Add a `speech_language` constructor argument to `AudioAgent` (sourced from the session row by `RuntimeRegistry`); pass it as the STT `language` hint on both the gateway (`client.audio.transcriptions.create`) and direct ElevenLabs calls; add a Hebrew filler/disfluency word set (`FILLERS_HE`, e.g. "אה", "אהמ", "כאילו", "סתם", "בעצם") and select `FILLERS` vs `FILLERS_HE` by `speech_language` instead of always using the English set. Files: `packages/backend/runtime.py`, `packages/backend/agents/audio_agent.py`.
- [X] T004 [ASYNC] [US1] Add `speech_language`/`deck_language` parameters to `PPTXAgent.analyse()` (sourced from the session row in `routers/upload.py`); instruct the LLM prompt to write `description`/`suggested_fix` in `speech_language`, with `deck_language` given as interpretive context for the extracted slide text; add Hebrew variants of `_FACTOR_FIX_TEMPLATES` and the deterministic description/fix strings in `_supplement_from_metadata`/`_default_suggested_fix`, selected by `speech_language`, so a deterministic fallback never silently writes English into a Hebrew-spoken session's findings. Files: `packages/backend/routers/upload.py`, `packages/backend/agents/pptx_agent.py`.

**Checkpoint**: User Story 1 is fully functional and testable independently — Hebrew rehearsal capture and voice coaching are accurate regardless of deck language.

---

## Phase 3: User Story 2 - Choose report language independent of spoken language (Priority: P1)

**Goal**: After a session ends, the user can view the report in Hebrew or English (defaulting to the declared speech language) and switch instantly, with the report view mirrored RTL when Hebrew is active.

**Independent Test**: Open the report for a Hebrew-spoken session, confirm it defaults to Hebrew and renders RTL, toggle to English and confirm an instant switch with no loading state, toggle back to Hebrew.

- [X] T005 [SYNC] [US2] Change `Insight.message: str` to `message_en: str` / `message_he: str` in the schema. In `ReportAgent.generate()`: render deterministic voice/body insights directly in both languages; have `ContentAnalysisAgent`'s prompt write in `speech_language`; make one batched LLM call that translates the LLM-derived findings (content + slide) into the other language; write both fields as part of the existing single `insert_report` call (no separate write — `ReportAgent` is this table's sole writer). On translation failure, set the missing field equal to the other (with a label) rather than failing the report. Files: `packages/backend/agents/schemas.py`, `packages/backend/agents/report_agent.py`, `packages/backend/agents/content_agent.py`.
- [X] T006 [ASYNC] [US2] Add an optional `?lang=en|he` query parameter to `GET /sessions/{id}/report`; default to the session's `speech_language` when omitted; add `language` and `speech_language` fields to the response; pick `insights[].message` from `message_en`/`message_he` — pure read, no write, no LLM call. File: `packages/backend/routers/sessions.py`.
- [X] T007 [P] [ASYNC] [US2] Add `language`/`speech_language` to `ReportData` and a `lang` parameter to `getReport(...)`. Files: `packages/shared-types/src/index.ts`, `packages/web-dashboard/app/lib/api.ts`.
- [X] T008 [SYNC] [US2] Add a language toggle to the report page; scope `dir="rtl"` to the report view and `ScoreCard` when Hebrew is active; keep status/score indicators distinguishable without relying on color in either direction. Files: `packages/web-dashboard/app/routes/session.$id_.report.tsx`, `packages/web-dashboard/app/components/ScoreCard.tsx`.
- [X] T009 [P] [ASYNC] [US2] Add a Hebrew-capable font dependency (e.g. `@fontsource-variable/noto-sans-hebrew`) and apply it to Hebrew text runs in the report view — the existing display fonts (Tektur, Chakra Petch, Space Mono, Geist) have no Hebrew glyphs. Files: `packages/web-dashboard/package.json`, report-view styles.

**Checkpoint**: User Stories 1 and 2 both work independently — the core demo path (Hebrew rehearsal → bilingual, RTL-correct report) is complete.

---

## Phase 4: User Story 3 - Use the dashboard UI in Hebrew with RTL layout (Priority: P3)

**Goal**: A user can set Hebrew as their interface language and get a correctly mirrored dashboard outside the report view too.

**Independent Test**: Set the interface language to Hebrew in Settings, reload, confirm `<html lang dir>` is correct on first paint with no flash, and that English/LTR is unaffected when left at the default.

- [X] T010 [ASYNC] [US3] Add a persisted interface-language cookie; read it in the root loader so `<html lang dir>` is correct on the very first server-rendered paint. File: `packages/web-dashboard/app/routes/__root.tsx`.
- [ ] T011 [P] [ASYNC] [US3] Add an interface-language preference row to Settings that writes the cookie. File: `packages/web-dashboard/app/routes/settings.tsx`.

**Checkpoint**: All three user stories are independently functional.

---

## Phase 5: Polish & Validation

- [ ] T012 [ASYNC] Add a Hebrew `DEMO_MODE=replay` audio fixture variant so the demo path is rehearsable without live STT (CAR-004). Files: `packages/backend/fixtures/`, `packages/backend/agents/replay_fixtures.py`.
- [ ] T013 [P] [ASYNC] Add pytest coverage for Hebrew filler-word detection (no cross-language false positives) and for bilingual insight assembly, per the Constitution's automated-test requirement for agent/scoring changes. Files: `packages/backend/tests/test_audio_agent.py` (new), `packages/backend/tests/test_report_dedup.py` (extend).
- [ ] T014 Run `quickstart.md` end-to-end (Path A live STT, Path B replay, backend contract checks, manual desktop/mobile UI verification) and confirm SC-001 through SC-005.

---

## Dependencies & Execution Order

- **Phase 1 (Foundational)**: No dependencies. Blocks every user story.
- **Phase 2 (US1)**: Depends on Phase 1 only. Independently demoable on its own.
- **Phase 3 (US2)**: Depends on Phase 1 only (reads `speech_language`; does not require US1's STT/filler work to be done, since it can be exercised with `DEMO_MODE=replay` or an English-spoken session). T006/T007/T008/T009 depend on T005.
- **Phase 4 (US3)**: Depends on Phase 1 only. Fully independent of US1/US2.
- **Phase 5 (Polish)**: Depends on Phases 2 and 3 (validates both MVP stories end-to-end); T010/T011 (US3) are not required for Polish to start.

### Parallel Opportunities

- T002 (frontend start-screen controls) can run in parallel with T003/T004 (backend agent wiring) once T001 is done.
- T007 and T009 (US2) can run in parallel with T005/T006 once T005 lands.
- T010 and T011 (US3) can run in parallel with everything in Phases 2–3 once Phase 1 is done.

---

## Implementation Strategy

**MVP**: Phase 1 → Phase 2 (US1) → Phase 3 (US2) → T014 validation. This is the full core demo path
(Hebrew rehearsal capture with accurate coaching, bilingual RTL-correct report) and is independently
demoable without Phase 4. Phase 4 (US3, full dashboard chrome) is the explicitly deferrable slice — add
it after the MVP is validated, per Constitution Principle I.
