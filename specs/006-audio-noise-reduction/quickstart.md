# Quickstart & Validation Guide: Audio Noise Reduction Pipeline

**Feature**: 006-audio-noise-reduction
**Date**: 2026-06-24

## Prerequisites

- Docker running, Postgres up (`make db-up`)
- `.env` with `LITELLM_API_KEY` and `ELEVENLABS_API_KEY` (or `DEMO_MODE=replay` for fixture mode)
- Dependencies installed: `make install`

---

## Scenario 1: Unit Tests Pass

Validates that the noise reduction utility works in isolation.

```bash
cd packages/backend
uv run pytest tests/test_noise_reduction.py -v
```

**Expected output**: 4 tests pass — happy path, silence, exception safety, short chunk.

---

## Scenario 2: Backend Starts Without Errors

Validates that the new `noisereduce` dependency loads correctly.

```bash
make backend
```

**Expected**: Server starts on port 8000. Log line `INFO: Application startup complete.` appears. No `ImportError` for `noisereduce` or `numpy`.

---

## Scenario 3: Replay Mode Still Works (DEMO_MODE=replay)

Validates that noise reduction is bypassed in demo mode and the core demo path is unaffected.

```bash
DEMO_MODE=replay make dev
```

1. Open `http://localhost:3000`
2. Upload any `.pptx` file
3. Start rehearsal session
4. Speak for a few seconds, then end session
5. Navigate to `/session/:id/report`

**Expected**: Report generates normally. No errors in backend logs related to `noise_reduction`. Backend logs should NOT show `apply_noise_reduction` being called (verify via `grep` or absence of noise reduction log lines).

---

## Scenario 4: Live Mode — Noise Reduction Applied Per Chunk

Validates the feature with live audio (requires API keys, not `DEMO_MODE=replay`).

```bash
make dev   # without DEMO_MODE=replay
```

1. Open `http://localhost:3000` in Chrome or Firefox
2. Start a rehearsal session
3. While speaking, play background noise from another device (e.g., crowd noise video at moderate volume)
4. End the session after 30–60 seconds
5. Navigate to `/session/:id/report`

**Expected**:
- Backend logs show: `Noise reduction applied to chunk N (Xms)` for each chunk
- Transcript in the report reflects only spoken words, not noise artifacts
- No backend errors or dropped chunks
- Report available within 60 seconds of session end

---

## Scenario 5: Browser Audio Constraints Active

Validates that the frontend requests the microphone with noise suppression enabled.

1. Open Chrome DevTools → Application → Permissions or Media tab
2. Start a rehearsal session
3. In DevTools Console: `navigator.mediaDevices.enumerateDevices().then(console.log)` — check that the active audio track has `noiseSuppression: true`

Alternatively, open `chrome://webrtc-internals` during an active session and inspect the `getUserMedia` call constraints under the audio section.

**Expected**: `noiseSuppression: true`, `echoCancellation: true`, `autoGainControl: true` visible in the constraint set.

---

## Scenario 6: Exception Fallback — Noise Reduction Disabled

Validates that a noise reduction failure does not block transcription.

Set `NOISE_REDUCTION_ENABLED=false` in `.env`, then run a live session.

**Expected**:
- Backend logs: noise reduction skipped or disabled
- Transcription proceeds normally with raw audio
- No errors; report generated as usual

---

## Key File References

| File | Purpose |
|---|---|
| `packages/backend/agents/noise_reduction.py` | Core noise reduction utility — pure function |
| `packages/backend/agents/audio_agent.py` | Integration point: call `apply_noise_reduction` at top of `push_chunk` |
| `packages/backend/pyproject.toml` | `noisereduce>=3.0` dependency |
| `packages/backend/config.py` | `noise_reduction_enabled` setting |
| `packages/backend/tests/test_noise_reduction.py` | Unit tests |
| `packages/web-dashboard/app/lib/capture.ts` | `getUserMedia` audio constraints |
