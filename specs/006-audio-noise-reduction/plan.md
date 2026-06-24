# Implementation Plan: Audio Noise Reduction Pipeline

**Branch**: `main` | **Date**: 2026-06-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/006-audio-noise-reduction/spec.md`

## Summary

Add two-stage audio noise reduction: (1) browser-side WebRTC constraints on the microphone stream, and (2) per-chunk spectral gating in `AudioAgent.push_chunk()` before each 2-second PCM chunk is sent to ElevenLabs Scribe. No new routes, no new DB schema, no downstream pipeline changes.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript (frontend)
**Primary Dependencies**: `noisereduce>=3.0` (new), `numpy` (already transitive), FastAPI, TanStack Start
**Storage**: N/A — noise reduction is stateless per-chunk; no new DB entities
**Testing**: pytest (backend unit tests for noise reduction utility)
**Target Platform**: Linux server (backend), modern desktop browser (frontend)
**Project Type**: Web application — streaming audio pipeline
**Performance Goals**: ≤500ms added latency per minute of audio (2s chunk → ≤~17ms per chunk)
**Constraints**: Must not block WS receive loop; fallback on exception; `DEMO_MODE=replay` bypasses entirely
**Scale/Scope**: Per-session, per-2s-chunk processing; single FastAPI process

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Demo-First Vertical Slices | ✅ PASS | Transparent improvement on the live rehearsal path. DEMO_MODE=replay still bypasses. Core demo path unchanged. |
| II. Contracted Agent Boundaries | ✅ PASS | AudioAgent retains sole ownership of transcript + audio_warning writes. No new agent writer introduced. Noise reduction is internal preprocessing within `push_chunk`. |
| III. Session Isolation | ✅ PASS | No changes to `access_token`, `share_token`, WebSocket auth, or session routing. |
| IV. Resilience Before Polish | ✅ PASS | Exception in noise reduction falls back to raw PCM + logs the error. `DEMO_MODE=replay` bypass required (FR-006). No new external provider dependency. |
| V. Native Stack, Minimal Abstractions | ✅ PASS (justified) | `noisereduce` is new. Justified: Python stdlib has no spectral noise gating; `webrtcvad` only does VAD (won't reduce noise during speech); `noisereduce` is a single-purpose library with no service/queue abstraction. Rejected simpler alternative: `webrtcvad` alone — cannot attenuate noise that overlaps with speech frames. |

**Post-design re-check**: ✅ All clear. No new routes, no schema changes, no new agents, no service boundaries introduced.

## Project Structure

### Documentation (this feature)

```text
specs/006-audio-noise-reduction/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/spec-tasks — NOT created here)
```

### Source Code (repository root)

```text
packages/backend/
├── agents/
│   ├── audio_agent.py          # MODIFY: call noise_reduction.apply() in push_chunk
│   └── noise_reduction.py      # NEW: noise reduction utility (isolated, testable)
├── pyproject.toml              # MODIFY: add noisereduce dependency
└── tests/
    └── test_noise_reduction.py # NEW: unit tests for the noise utility

packages/web-dashboard/
└── app/
    └── lib/
        └── capture.ts          # MODIFY: add audio constraints to getUserMedia call
```

**Structure Decision**: Monorepo layout unchanged. Noise reduction isolated in its own module (`noise_reduction.py`) so it can be unit-tested and swapped without touching agent logic beyond the single call site.

## Triage Framework: [SYNC] vs [ASYNC] Classification

**Execution Strategy**: Hybrid — routine edits delegated, sensitive fallback logic reviewed by human.

### Preliminary Task Classification

| Task Category | Estimated [SYNC] Tasks | Estimated [ASYNC] Tasks | Rationale |
|---|---|---|---|
| Business Logic | 1 | 1 | Fallback/exception path = SYNC; core reduction logic = ASYNC |
| Data Operations | 0 | 0 | No DB changes |
| UI Components | 0 | 1 | getUserMedia constraint change is straightforward |
| Integrations | 1 | 0 | AudioAgent integration point touches live STT path = SYNC review |
| Infrastructure | 0 | 1 | Dependency add is mechanical |

### Triage Decision Criteria Applied

**High-Risk [SYNC] Classifications:**
- `AudioAgent.push_chunk()` integration — fallback exception handling and `DEMO_MODE=replay` bypass must be correct; a bug here drops transcripts silently
- `noise_reduction.py` exception contract — must never raise; caller depends on fallback behavior

**Agent-Delegated [ASYNC] Classifications:**
- `capture.ts` getUserMedia constraint addition
- `pyproject.toml` dependency addition
- `test_noise_reduction.py` unit test scaffolding
- Core spectral reduction implementation in `noise_reduction.py`

### Triage Audit Trail

| Task | Classification | Primary Criteria | Risk Level | Rationale |
|---|---|---|---|---|
| Add `noisereduce` to pyproject.toml | ASYNC | Mechanical dependency bump | Low | No logic; uv add |
| Implement `noise_reduction.py` | ASYNC | Isolated utility, no DB/WS | Low | Fully unit-testable, no side effects |
| Unit tests for noise_reduction | ASYNC | Standard pytest | Low | Covers happy path and fallback |
| Modify `push_chunk` in AudioAgent | SYNC | Live STT path, fallback critical | Medium | Must not break transcript flow |
| Modify `startAudioCapture` in capture.ts | ASYNC | Frontend constraint change | Low | Graceful fallback built-in |

## Complexity Tracking

No constitution violations. Table not required.
