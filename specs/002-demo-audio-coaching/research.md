# Phase 0 Research: Demo Audio Coaching

## Browser Audio Capture Format

**Decision**: Capture microphone audio in the browser as mono 16 kHz signed 16-bit little-endian PCM, sent as binary WebSocket chunks to `/audio-stream` every 2 seconds.

**Rationale**: This matches `packages/web-dashboard/app/lib/capture.ts`, `Settings.audio_chunk_seconds`, and `AudioAgent._wrap_pcm_as_wav`. Two-second chunks keep demo feedback reasonably fresh without excessive STT overhead.

**Alternatives considered**: `MediaRecorder` WebM/Opus would simplify browser code but requires backend decoding. Sub-second chunks increase provider and WebSocket churn. Five-second chunks reduce overhead but make live warnings and report evidence feel late.

## PCM-to-WAV Boundary

**Decision**: Keep the wire contract as raw PCM and wrap each chunk in a minimal RIFF/WAVE container on the backend before sending to STT.

**Rationale**: Scribe-compatible transcription APIs expect an audio container, while raw PCM keeps the frontend contract simple and testable. Existing `test_wav_header.py` validates the generated WAV structure.

**Alternatives considered**: Browser-generated WAV duplicates container work on every client. Sending raw PCM directly to providers is likely to fail. Adding an audio transcoder package is unnecessary for demo scope.

## STT Provider Order and Failure Behavior

**Decision**: Use LiteLLM's OpenAI-compatible transcription call as the primary STT path; use direct ElevenLabs Scribe v1 fallback when `ELEVENLABS_API_KEY` is configured; allow `PROVIDER_MODE=direct` to flip provider order for demo emergencies.

**Rationale**: The repo already implements this via `get_llm`, `pick_provider_order`, and direct ElevenLabs HTTP fallback. It gives the team a fast operational switch if gateway quota or routing fails.

**Alternatives considered**: Gateway-only is simpler but brittle on demo day. Direct-only requires personal credentials and bypasses the intended shared gateway. Automatic multi-provider fanout adds complexity and cost without a one-day payoff.

## Empty, Slow, or Failed STT Responses

**Decision**: Empty text, silence, and provider errors must not block `POST /sessions/:id/end` or report access. In normal mode, no usable speech should produce a clear no-audio/insufficient-audio voice outcome. In replay mode, prepared audio evidence may be used explicitly.

**Rationale**: The feature exists for one live demo. A coherent report or clear no-audio state is more valuable than perfect transcription accuracy.

**Alternatives considered**: Aggressive retries per chunk risk backpressure and report delays. Silently fabricating fallback evidence outside `DEMO_MODE=replay` would undermine trust.

## Demo Replay Semantics

**Decision**: `DEMO_MODE=replay` should emit prepared audio events once per session, not once per received audio chunk.

**Rationale**: Current per-chunk replay can duplicate transcript and warning rows, directly violating FR-009 and SC-005. Replay is demo insurance, but it must not make the database or UI look broken.

**Alternatives considered**: Rely on final report deduplication only. Rejected because duplicate live warnings and transcript rows can still be visible or affect counts.

## Replay Fixture Immutability

**Decision**: Treat `audio_events.json` rows as immutable source data and copy each raw object before deriving or removing `kind`.

**Rationale**: `replay_audio_events()` currently calls `raw.pop("kind", ...)` against cached JSON objects. That can corrupt subsequent calls and makes repeated dry runs unreliable.

**Alternatives considered**: Disable fixture caching. This is acceptable but less minimal than copying rows before mutation.

## Transcript and Warning Deduplication

**Decision**: Deduplicate fallback/live audio evidence at write-time using natural keys and continue grouping repeated issues in `ReportAgent`.

**Rationale**: Report grouping already consolidates insights, but duplicate persisted rows can still inflate counts, timestamps, and live feedback. Write-time dedup protects the source of truth.

**Alternatives considered**: UI-only filtering hides symptoms and leaves corrupted source data. Database unique constraints are stronger but may be too invasive for one-day scope unless implemented carefully.

## Filler Word Detection

**Decision**: Detect obvious fillers deterministically from transcript text, with at least `um` and `uh` case-insensitive on word boundaries. Treat ambiguous fillers like `like` conservatively unless repeated or clearly filler-like in the demo script.

**Rationale**: Deterministic text matching is explainable, cheap, and easy to test. The spec explicitly warns against over-penalizing ambiguous words.

**Alternatives considered**: LLM-based filler classification is slower and less deterministic. Counting every `like` is simple but visibly unfair.

## Pacing Detection

**Decision**: Calculate WPM over a sustained rolling speech window with a minimum evidence gate and debounce warnings for roughly 10 seconds.

**Rationale**: Single 2-second chunks are too noisy. The current 30-second window is stable, but tasks should validate that the planned 10-second fast segment can still trigger a useful finding.

**Alternatives considered**: Whole-session WPM misses local pacing problems. Per-chunk WPM creates false positives and distracting live warnings.

## Live Warning Throttling

**Decision**: Throttle repeated live warnings server-side by session and warning type/message while still recording transcript evidence for the final report.

**Rationale**: Frontend-only throttling does not protect multiple clients or persisted event spam. The spec requires live warnings to be non-blocking and not distract from rehearsal.

**Alternatives considered**: Keep only the current pacing debounce. Rejected because filler warnings can still fire repeatedly across chunks.

## Session Isolation

**Decision**: Keep capability-token WebSocket auth and require inbound audio writes to target an active session. Ended sessions should reject or ignore new audio chunks.

**Rationale**: Session tokens are the security boundary, and late reconnects after report generation must not mutate the completed report's source data.

**Alternatives considered**: Full user accounts/JWTs are overkill. Token validation without active-state checks leaves a lifecycle hole.

## Testing Strategy

**Decision**: Use deterministic backend pytest coverage for WAV wrapping, filler matching, WPM warnings/debounce, replay idempotency, mocked provider fallback, report deduplication, and WebSocket auth/session-state behavior. Use manual frontend validation for microphone permission/device-loss copy and responsive report/session pages.

**Rationale**: Live provider tests are flaky and unsafe for CI/demo prep. The important behavior can be covered through pure helper tests, mocked HTTP/provider calls, and existing FastAPI TestClient patterns.

**Alternatives considered**: Manual-only demo dry runs are necessary but insufficient. End-to-end browser automation is useful but too expensive to make the only validation layer.
