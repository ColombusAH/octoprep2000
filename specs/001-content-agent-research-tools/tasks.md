---
description: "Task list for Content Agent Research Tools feature"
---

# Tasks: Content Agent Research Tools

**Input**: Design documents from `/specs/001-content-agent-research-tools/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/content-research.md, quickstart.md

**Tests**: Backend agent/scoring changes require automated tests per constitution. Test tasks included for research module, degradation, and report status insight.

**Organization**: Tasks grouped by user story (US1 grounded accuracy, US3 resilience, US2 improvement enrichment).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to spec.md user stories (US1, US2, US3)

## Path Conventions

- Backend: `packages/backend/`
- Frontend: `packages/web-dashboard/`
- Shared types: `packages/shared-types/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies, config, and package skeleton

- [x] T001 Add `exa-py` dependency to `packages/backend/pyproject.toml` and run `uv sync` in backend package
- [x] T002 [P] Add research settings (`exa_api_key`, `context7_api_key`, `content_research_enabled`, `content_research_timeout_s`) to `packages/backend/config.py`
- [x] T003 [P] Document new env vars in `.env.example` (`EXA_API_KEY`, `CONTEXT7_API_KEY`, `CONTENT_RESEARCH_ENABLED`, `CONTENT_RESEARCH_TIMEOUT_S`)
- [x] T004 [P] Create `packages/backend/agents/content_research/` package with `__init__.py` and `errors.py` (`ResearchProviderError`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared models and schema extensions required by all user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement `TopicClassification`, `ReferenceSnippet`, and `ReferenceBundle` with excerpt caps in `packages/backend/agents/content_research/reference_bundle.py`
- [x] T006 Implement `classify_topic()` using text model structured output in `packages/backend/agents/content_research/classifier.py`
- [x] T007 Extend `ContentAnalysisPayload` with optional `research_status` field in `packages/backend/agents/schemas.py`
- [x] T008 [P] Add `research_status` default handling in `packages/backend/agents/replay_fixtures.py` for `replay_content_analysis()`
- [x] T009 [P] Create `packages/backend/agents/content_research/fetcher.py` stub with `fetch_reference_bundle()` signature per `contracts/content-research.md`
- [x] T010 [P] Add unit tests for classifier threshold and bundle caps in `packages/backend/tests/test_content_research.py`

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 - Grounded Technical Accuracy Check (Priority: P1) 🎯 MVP

**Goal**: Technical sessions fetch official docs (Context7) and articles (Exa) before LLM evaluation; findings reflect retrieved reference material.

**Independent Test**: End a technical session with a transcript containing a verifiable claim and an omission. Report Technical Content panel shows coverage-gap or factual-error findings aligned with retrieved sources (`quickstart.md` Scenario 1).

### Implementation for User Story 1

- [x] T011 [P] [US1] Implement `resolve_library()` and `fetch_docs()` via httpx in `packages/backend/agents/content_research/context7_client.py`
- [x] T012 [P] [US1] Implement `search_articles()` with highlights in `packages/backend/agents/content_research/exa_client.py`
- [x] T013 [US1] Implement parallel Context7 + Exa fetch with snippet merge in `packages/backend/agents/content_research/fetcher.py`
- [x] T014 [US1] Add `_build_evaluation_prompt()` injecting docs/articles blocks in `packages/backend/agents/content_agent.py`
- [x] T015 [US1] Wire classify → fetch → evaluate pipeline for technical topics in `packages/backend/agents/content_agent.py`
- [x] T016 [US1] Update `CONTENT_PROMPT` to prefer official docs over articles for factual disputes in `packages/backend/agents/content_agent.py`
- [x] T017 [P] [US1] Add httpx mock tests for Context7 client in `packages/backend/tests/test_content_research.py`
- [x] T018 [P] [US1] Add stubbed Exa client tests for article snippets in `packages/backend/tests/test_content_research.py`

**Checkpoint**: Technical topics produce research-grounded content findings when API keys are configured

---

## Phase 4: User Story 3 - Safe Degradation and Demo Continuity (Priority: P1)

**Goal**: Report generation never blocks on research failures; replay mode unchanged; users see explicit research status.

**Independent Test**: Run `quickstart.md` Scenarios 2–4 — replay fixtures, missing API keys, and non-technical topics all complete with appropriate `content_research_status`.

### Implementation for User Story 3

- [x] T019 [US3] Apply `asyncio.wait_for` wall-clock budget per provider in `packages/backend/agents/content_research/fetcher.py`
- [x] T020 [US3] Compute `research_status` (`full`/`partial`/`skipped`/`not_applicable`) in `packages/backend/agents/content_agent.py`
- [x] T021 [US3] Preserve early `demo_replay` return before any research in `packages/backend/agents/content_agent.py`
- [x] T022 [US3] Skip research when `classify_topic` returns non-technical or low confidence in `packages/backend/agents/content_agent.py`
- [x] T023 [US3] On research failure, continue with transcript-only LLM call (never return `None` solely due to research) in `packages/backend/agents/content_agent.py`
- [x] T024 [US3] Prepend status insight for `partial`/`skipped` in `packages/backend/agents/report_agent.py` `_content_breakdown()`
- [x] T025 [US3] Expose `content_research_status` in `GET /sessions/{id}/report` response in `packages/backend/routers/sessions.py`
- [x] T026 [P] [US3] Add degradation and replay-bypass tests in `packages/backend/tests/test_content_research.py`
- [x] T027 [P] [US3] Add report status insight test in `packages/backend/tests/test_content_research.py` or `packages/backend/tests/test_report_dedup.py`

**Checkpoint**: All resilience paths pass; demo path protected

---

## Phase 5: User Story 2 - Improvement-Oriented Research Enrichment (Priority: P2)

**Goal**: Improvement insights reflect best practices, pitfalls, and audience expectations from dedicated Exa improvement queries.

**Independent Test**: Technical session with partial coverage yields improvement insights referencing specific enhancements (`quickstart.md` Scenario 1 — review improvement messages for topic specificity).

### Implementation for User Story 2

- [x] T028 [P] [US2] Implement `search_improvements()` in `packages/backend/agents/content_research/exa_client.py`
- [x] T029 [US2] Include improvement snippets in `fetch_reference_bundle()` in `packages/backend/agents/content_research/fetcher.py`
- [x] T030 [US2] Add `improvement_block` section to `_build_evaluation_prompt()` in `packages/backend/agents/content_agent.py`
- [x] T031 [US2] Extend `CONTENT_PROMPT` to require improvement-grounded `COVERAGE_GAP` and actionable pitfall callouts in `packages/backend/agents/content_agent.py`
- [x] T032 [P] [US2] Add improvement query tests with stubbed Exa in `packages/backend/tests/test_content_research.py`

**Checkpoint**: Improvement findings are distinct from generic LLM advice when Exa returns results

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: UI surfacing, shared types, docs, end-to-end validation

- [x] T033 [P] Add `content_research_status` to `ReportData` type in `packages/web-dashboard/app/components/ScoreCard.tsx`
- [x] T034 Update disclaimer and research status text (text-only, not color-only) in `packages/web-dashboard/app/components/ScoreCard.tsx`
- [x] T035 [P] Add `content_research_status` to report type in `packages/shared-types/src/index.ts`
- [x] T036 [P] Wire `content_research_status` from API response in report route loader (e.g. `packages/web-dashboard/app/routes/session.$id.report.tsx` or equivalent)
- [x] T037 Verify `DEMO_MODE=replay`, missing keys, and `/health` unaffected — manual check per `specs/001-content-agent-research-tools/quickstart.md`
- [x] T038 Run `uv run pytest packages/backend/tests/test_content_research.py packages/backend/tests/test_report_dedup.py -q` and fix failures
- [x] T039 [P] Update `CLAUDE.md` / `README.md` env var table for research keys if not already documented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → **US1 (Phase 3)** + **US3 (Phase 4)** can overlap after T013
- **US2 (Phase 5)** depends on US1 fetcher (`T013`) and US3 status plumbing (`T020`)
- **Polish (Phase 6)** depends on US3 API field (`T025`) and preferably US2 complete

### User Story Dependencies

| Story | Depends on | Independent test |
|---|---|---|
| **US1** | Foundational (Phase 2) | Technical session + live keys → grounded findings |
| **US3** | Foundational; integrates with US1 pipeline | Replay / missing keys / non-technical scenarios |
| **US2** | US1 fetcher | Improvement-specific Exa queries in findings |

### Parallel Opportunities

- **Phase 1**: T002, T003, T004 in parallel after T001
- **Phase 2**: T008, T009, T010 in parallel after T007
- **Phase 3**: T011 + T012 in parallel; T017 + T018 in parallel after T015
- **Phase 4**: T026 + T027 in parallel after T024
- **Phase 5**: T028 parallel with prior work if fetcher interface stable
- **Phase 6**: T033, T035, T036, T039 in parallel

### Parallel Example: User Story 1

```bash
# Launch provider clients together:
Task T011: context7_client.py
Task T012: exa_client.py (articles)

# Launch tests together after pipeline wired:
Task T017: Context7 mock tests
Task T018: Exa stub tests
```

---

## Implementation Strategy

### MVP First (US1 + US3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (grounded accuracy)
4. Complete Phase 4: US3 (resilience + status surfacing)
5. **STOP and VALIDATE**: `quickstart.md` Scenarios 1–4
6. Demo-safe with `DEMO_MODE=replay` verified

### Incremental Delivery

1. Setup + Foundational → scaffolding ready
2. US1 + US3 → **MVP** (accurate + resilient)
3. US2 → improvement enrichment
4. Polish → UI + docs + full test pass

### Suggested MVP Scope

**Phases 1–4** (T001–T027): Grounded technical analysis with full degradation story. US2 improvement queries can ship as fast follow without blocking demo.

---

## Notes

- Total tasks: **39** (Setup 4, Foundational 6, US1 8, US3 9, US2 5, Polish 7)
- Task count per story: US1 = 8, US3 = 9, US2 = 5
- OpenSearch optional backend deferred — not in task list; add later if `OPENSEARCH_URL` is configured
- Keep `ContentAnalysisPayload` backward-compatible; `research_status` optional with default `not_applicable`
- Do not call `Orchestrator.on_content_analysis()` — report path remains via `ReportAgent` only
