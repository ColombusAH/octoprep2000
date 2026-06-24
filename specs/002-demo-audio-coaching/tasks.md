# Tasks: Demo Audio Coaching

**Input**: Design documents from `/specs/002-demo-audio-coaching/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/audio-coaching-contract.md`, `quickstart.md`
**Tests**: Included. The specification, quickstart, and constitution explicitly require backend validation for route, payload, fallback, deduplication, scoring, and WebSocket behavior.
**Organization**: Tasks are grouped by independently testable user story in priority order.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm demo-day configuration and replay fixture inputs before code work.

- [ ] T001 [P] Verify `.env.example` documents `DEMO_MODE=replay`, `PROVIDER_MODE=direct`, `LITELLM_API_KEY`, and `ELEVENLABS_API_KEY` for audio demo fallback behavior
- [ ] T002 [P] Verify `packages/backend/fixtures/audio_events.json` contains transcript and warning rows matching `specs/002-demo-audio-coaching/contracts/audio-coaching-contract.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Protect session isolation and source-of-truth audio persistence before any user story implementation.

**Critical**: No user story work should begin until this phase is complete.

- [ ] T003 [P] Add active-session `/audio-stream` rejection tests for ended sessions in `packages/backend/tests/test_ws_auth.py`
- [ ] T004 [P] Add transcript and audio warning natural-key deduplication tests in `packages/backend/tests/test_audio_repository.py`
- [ ] T005 Add active-session validation support for WebSocket auth in `packages/backend/middleware/session_auth.py`
- [ ] T006 Add per-session natural-key deduplication for transcript entries and audio warnings in `packages/backend/db/repository.py`
- [ ] T007 Thread active-session validation through `/audio-stream` before accepting or processing chunks in `packages/backend/routers/audio_ws.py`
- [ ] T008 Run `cd packages/backend && uv run pytest tests/test_ws_auth.py tests/test_audio_repository.py` and fix failures in `packages/backend/middleware/session_auth.py`, `packages/backend/db/repository.py`, and `packages/backend/routers/audio_ws.py`

**Checkpoint**: Authorized active sessions can publish audio, ended sessions cannot mutate audio evidence, and duplicate persisted audio evidence is blocked.

---

## Phase 3: User Story 1 - Capture Speech Feedback (Priority: P1)

**Goal**: Capture browser microphone audio, transcribe recognizable speech, detect obvious filler and pacing issues, and render transcript-backed voice feedback in the final report.

**Independent Test**: Start a short practice session, speak a known 30-60 second script containing `um` or `uh` plus a deliberate fast segment, end the session, and verify the report contains transcript-backed voice insights with timestamps.

### Tests for User Story 1

- [ ] T009 [P] [US1] Add filler word boundary and conservative ambiguous `like` policy tests in `packages/backend/tests/test_audio_filler.py`
- [ ] T010 [P] [US1] Add sustained WPM pacing threshold and warning debounce tests in `packages/backend/tests/test_audio_pacing.py`
- [ ] T011 [P] [US1] Add mocked `AudioAgent.push_chunk` transcript/warning emission tests in `packages/backend/tests/test_audio_agent.py`
- [ ] T012 [P] [US1] Extend voice report timestamp and scoring tests for filler and pacing evidence in `packages/backend/tests/test_report_dedup.py`

### Implementation for User Story 1

- [ ] T013 [US1] Replace broad filler matching with deterministic `um`/`uh` detection and conservative `like` handling in `packages/backend/agents/audio_agent.py`
- [ ] T014 [US1] Adjust WPM calculation to require sustained evidence while still detecting a 10-second fast segment in `packages/backend/agents/audio_agent.py`
- [ ] T015 [US1] Ensure `AudioAgent.push_chunk` emits transcript entries before derived warnings and skips empty STT output in `packages/backend/agents/audio_agent.py`
- [ ] T016 [US1] Ensure `ReportAgent._score_voice` produces clear timestamped filler and pacing insights from persisted evidence in `packages/backend/agents/report_agent.py`
- [ ] T017 [US1] Run `cd packages/backend && uv run pytest tests/test_audio_filler.py tests/test_audio_pacing.py tests/test_audio_agent.py tests/test_report_dedup.py` and fix failures in `packages/backend/agents/audio_agent.py` and `packages/backend/agents/report_agent.py`

**Checkpoint**: User Story 1 is independently functional when live STT returns usable speech.

---

## Phase 4: User Story 2 - Keep the Demo Alive on Audio Failure (Priority: P2)

**Goal**: Keep session completion and report access reliable when STT, replay, or microphone capture fails, without duplicate fallback evidence.

**Independent Test**: Run a session with live transcription unavailable or `DEMO_MODE=replay`, complete the session, and verify the user reaches a coherent report or clear no-audio outcome with no duplicated prepared transcript or warning rows.

### Tests for User Story 2

- [ ] T018 [P] [US2] Add replay fixture immutability tests for cached JSON rows in `packages/backend/tests/test_replay_fixtures.py`
- [ ] T019 [P] [US2] Add `DEMO_MODE=replay` once-per-session tests for repeated audio chunks in `packages/backend/tests/test_audio_replay.py`
- [ ] T020 [P] [US2] Add mocked STT provider fallback tests for gateway-first, direct-first, empty text, and provider errors in `packages/backend/tests/test_audio_stt.py`
- [ ] T021 [P] [US2] Add no-audio and insufficient-audio report outcome tests in `packages/backend/tests/test_report_dedup.py`

### Implementation for User Story 2

- [ ] T022 [US2] Copy replay fixture rows before reading or removing `kind` in `packages/backend/agents/replay_fixtures.py`
- [ ] T023 [US2] Track replay dispatch so prepared audio events emit at most once per `AudioAgent` session in `packages/backend/agents/audio_agent.py`
- [ ] T024 [US2] Ensure gateway/direct STT provider errors and empty text return without blocking audio chunk processing in `packages/backend/agents/audio_agent.py`
- [ ] T025 [US2] Preserve report generation for no usable speech with a clear numeric voice outcome and voice insight in `packages/backend/agents/report_agent.py`
- [ ] T026 [US2] Keep microphone capture failure as a clear non-blocking text warning while allowing session end when video capture still works in `packages/web-dashboard/app/routes/session.$id.tsx`
- [ ] T027 [US2] Ensure report loading and error states remain clear text outcomes when no audio was captured or report retrieval is delayed in `packages/web-dashboard/app/routes/session.$id_.report.tsx`
- [ ] T028 [US2] Run `cd packages/backend && uv run pytest tests/test_replay_fixtures.py tests/test_audio_replay.py tests/test_audio_stt.py tests/test_report_dedup.py` and fix failures in `packages/backend/agents/replay_fixtures.py`, `packages/backend/agents/audio_agent.py`, and `packages/backend/agents/report_agent.py`

**Checkpoint**: User Story 2 is independently functional when live STT fails, replay is enabled, or microphone capture is denied.

---

## Phase 5: User Story 3 - Show Live Coaching When Enabled (Priority: P3)

**Goal**: Show optional non-blocking live warnings for filler and pacing while preserving final report evidence when live warnings are disabled.

**Independent Test**: Enable live feedback, say `um` or `uh`, verify a non-blocking warning appears during the session, then repeat with live feedback disabled and verify the final report still contains voice evidence.

### Tests for User Story 3

- [ ] T029 [P] [US3] Add server-side repeated live warning throttle tests in `packages/backend/tests/test_audio_live_warnings.py`

### Implementation for User Story 3

- [ ] T030 [US3] Add per-session warning throttling for repeated filler and pacing live warnings in `packages/backend/agents/audio_agent.py`
- [ ] T031 [US3] Ensure live-warning throttling does not suppress transcript persistence for final report evidence in `packages/backend/agents/audio_agent.py`
- [ ] T032 [US3] Keep shared feedback payload types aligned for audio warnings and `FALLBACK_ACTIVATED` in `packages/shared-types/src/index.ts`
- [ ] T033 [US3] Verify the live-feedback toggle only displays audio warning toasts when enabled in `packages/web-dashboard/app/routes/session.$id.tsx`
- [ ] T034 [US3] Run `cd packages/backend && uv run pytest tests/test_audio_live_warnings.py tests/test_audio_agent.py` and fix failures in `packages/backend/agents/audio_agent.py`

**Checkpoint**: User Story 3 is independently functional without changing the final-report-first behavior.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate the full demo flow, document changed behavior, and run quality gates.

- [ ] T035 [P] Update `specs/002-demo-audio-coaching/quickstart.md` with final dry-run results for live audio, replay fallback, microphone failure, live feedback, and WebSocket isolation
- [ ] T036 [P] Update `docs/TECH-ARCHITECTURE-C4.md` if endpoint, payload, fallback, or scoring behavior changed during implementation
- [ ] T037 Run `cd packages/backend && uv run ruff check .` and fix lint failures in `packages/backend`
- [ ] T038 Run `cd packages/backend && uv run pytest` and fix test failures in `packages/backend`
- [ ] T039 Run `pnpm --filter @octoprep/web-dashboard lint` and fix lint/type failures in `packages/web-dashboard`
- [ ] T040 Run `make lint` and `make test` from `Makefile`, documenting any package-script limitation in `specs/002-demo-audio-coaching/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion and is the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational completion; can start after US1 tests define the audio-agent behavior, but should remain independently testable.
- **User Story 3 (Phase 5)**: Depends on Foundational completion; safest after US1 because it reuses the same detection paths.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 Capture Speech Feedback**: MVP, no dependency on US2 or US3 after Foundational.
- **US2 Keep the Demo Alive on Audio Failure**: Builds on the same persistence/report contracts as US1, but can be validated independently with replay or no-audio scenarios.
- **US3 Show Live Coaching When Enabled**: Builds on US1 detection and broadcaster behavior, but final report evidence must remain independent of the live-feedback toggle.

### Parallel Opportunities

- T001 and T002 can run in parallel.
- T003 and T004 can run in parallel before T005-T007.
- T009-T012 can run in parallel because they target separate focused test files or already scoped report tests.
- T018-T021 can run in parallel because they target separate fallback/replay/STT/report concerns.
- T026 and T027 can run in parallel with backend US2 implementation after expected failure behavior is agreed.
- T029 can run while US3 implementation design is reviewed.
- T035 and T036 can run in parallel after implementation behavior is stable.

---

## Parallel Example: User Story 1

```bash
Task: "T009 Add filler word boundary and conservative ambiguous like policy tests in packages/backend/tests/test_audio_filler.py"
Task: "T010 Add sustained WPM pacing threshold and warning debounce tests in packages/backend/tests/test_audio_pacing.py"
Task: "T011 Add mocked AudioAgent.push_chunk transcript/warning emission tests in packages/backend/tests/test_audio_agent.py"
Task: "T012 Extend voice report timestamp and scoring tests for filler and pacing evidence in packages/backend/tests/test_report_dedup.py"
```

## Parallel Example: User Story 2

```bash
Task: "T018 Add replay fixture immutability tests for cached JSON rows in packages/backend/tests/test_replay_fixtures.py"
Task: "T019 Add DEMO_MODE=replay once-per-session tests for repeated audio chunks in packages/backend/tests/test_audio_replay.py"
Task: "T020 Add mocked STT provider fallback tests in packages/backend/tests/test_audio_stt.py"
Task: "T021 Add no-audio and insufficient-audio report outcome tests in packages/backend/tests/test_report_dedup.py"
```

## Parallel Example: User Story 3

```bash
Task: "T029 Add server-side repeated live warning throttle tests in packages/backend/tests/test_audio_live_warnings.py"
Task: "T033 Verify the live-feedback toggle only displays audio warning toasts when enabled in packages/web-dashboard/app/routes/session.$id.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 Setup.
2. Complete Phase 2 Foundational session isolation and deduplication.
3. Complete Phase 3 User Story 1.
4. Stop and validate the known-script live STT path before adding fallback or live-warning polish.

### Incremental Delivery

1. Add US1 to prove transcript-backed voice findings in the final report.
2. Add US2 to make the demo resilient to STT, replay, and microphone failures.
3. Add US3 only after final report behavior is reliable.
4. Run Phase 6 checks and quickstart dry runs before declaring the feature complete.

### Parallel Team Strategy

1. One developer handles Foundational session/auth/dedup tasks.
2. One developer handles US1 deterministic audio-agent and report tests.
3. One developer handles US2 replay/STT fallback hardening.
4. One developer handles US3 live feedback and frontend manual validation.

---

## Notes

- `[P]` means the task can run in parallel because it targets different files or does not depend on incomplete implementation tasks.
- User story task labels `[US1]`, `[US2]`, and `[US3]` map directly to the prioritized stories in `spec.md`.
- Tests should be written first and observed failing before implementation tasks in the same story.
- Orchestrator remains the sole database writer; do not let agents write directly to PostgreSQL.
- Do not add new packages, queues, services, or storage layers for this feature.
