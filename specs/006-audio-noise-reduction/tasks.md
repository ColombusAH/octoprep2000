---
description: "Minimum tasks for audio noise reduction pipeline"
---

# Tasks: Audio Noise Reduction Pipeline

**Input**: Design documents from `specs/006-audio-noise-reduction/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

## Format: `[ID] [P?] [SYNC/ASYNC] [Story] Description`

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: New dependency and isolated utility — must be complete before any story work.

- [x] T001 [ASYNC] Add `noisereduce>=3.0` to `packages/backend/pyproject.toml` dependencies
- [x] T002 [P] [ASYNC] Add `noise_reduction_enabled: bool = True` setting to `packages/backend/config.py` Settings class
- [x] T003 [SYNC] Create `packages/backend/agents/noise_reduction.py` — pure function `apply_noise_reduction(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes`: convert PCM int16 to float32 numpy array, call `noisereduce.reduce_noise(y=audio, sr=sample_rate, stationary=False, prop_decrease=0.75)`, clip and convert back to int16 bytes; catch all exceptions, log and return input unchanged; skip if `get_settings().noise_reduction_enabled` is False

**Checkpoint**: `uv run python -c "from agents.noise_reduction import apply_noise_reduction; print('ok')"` exits 0.

---

## Phase 2: User Story 1 — Clean Transcription Despite Audience Noise (Priority: P1) 🎯 MVP

**Goal**: Backend reduces noise on each 2s PCM chunk before ElevenLabs STT.

**Independent Test**: Run `make backend`, start a session with noisy audio — backend logs show `apply_noise_reduction` called per chunk; transcription still completes.

- [x] T004 [SYNC] [US1] Modify `packages/backend/agents/audio_agent.py` `push_chunk()` method: after the `demo_replay` early-return block (after line ~116), add `pcm_bytes = apply_noise_reduction(pcm_bytes)` — import `apply_noise_reduction` from `agents.noise_reduction`
- [x] T005 [P] [ASYNC] [US1] Add unit tests in `packages/backend/tests/test_noise_reduction.py`: (1) white-noise-added PCM is changed by apply_noise_reduction, (2) all-zero PCM returns near-zero, (3) non-PCM bytes return input unchanged without raising, (4) chunk shorter than 0.5s does not raise

**Checkpoint**: `uv run pytest tests/test_noise_reduction.py -v` passes all 4 tests.

---

## Phase 3: User Story 2 — Browser Captures Clean Audio by Default (Priority: P2)

**Goal**: Microphone stream uses `noiseSuppression`, `echoCancellation`, `autoGainControl`.

**Independent Test**: Chrome DevTools → `chrome://webrtc-internals` shows audio constraints active during session recording.

- [x] T006 [P] [ASYNC] [US2] Modify `packages/web-dashboard/app/lib/capture.ts` `startAudioCapture()`: replace `getUserMedia({ audio: true })` with `getUserMedia({ audio: { noiseSuppression: true, echoCancellation: true, autoGainControl: true } }).catch(() => getUserMedia({ audio: true }))` — preserves existing fallback if browser rejects enriched constraints

**Checkpoint**: `startAudioCapture` compiles without TypeScript errors (`pnpm --filter web-dashboard typecheck`).

---

## Dependencies & Execution Order

- **Phase 1** (T001–T003): No dependencies — start immediately. T001 and T002 can run in parallel. T003 depends on T001 (noisereduce must be available).
- **Phase 2** (T004–T005): Depends on Phase 1 complete. T004 and T005 can run in parallel.
- **Phase 3** (T006): Independent of Phases 1–2 — can run in parallel with Phase 2 if staffed.

### MVP Scope

Complete Phases 1 and 2 only (T001–T005). US1 delivers the primary value (clean STT transcription). US2 (browser constraints) is additive polish.

---

## Notes

- No DB migrations required
- No new routes or contracts
- `DEMO_MODE=replay` bypass is already handled by the existing early-return in `push_chunk` — T004 injects AFTER that block, so no additional demo guard needed
