# Research: Audio Noise Reduction Pipeline

**Feature**: 006-audio-noise-reduction
**Date**: 2026-06-24

## Audio Architecture Discovery

### Finding: Audio is streamed live, not uploaded as a file

**Decision**: Noise reduction must operate per 2-second PCM chunk, not on a full recording.

**Rationale**: `audio_ws.py` receives raw binary PCM from the browser and immediately passes it to `AudioAgent.push_chunk()`. There is no post-session audio file. Each chunk is 2s × 16kHz × 2 bytes = 64,000 bytes of PCM 16-bit mono.

**Implications**:
- Noise profile cannot be estimated from a complete recording
- `noisereduce(stationary=False)` handles this: it adapts its noise estimate per chunk using short-time statistics rather than a global pre-recorded profile
- Processing overhead budget: 2s chunk → must complete in <<2s (soft); hard limit is 500ms (FR-007)

**Alternatives considered**: Accumulate all chunks and process at session end → rejected because the live transcript must be available as chunks arrive (report generation depends on timestamped entries written incrementally).

---

## Library Selection: noisereduce vs alternatives

### Decision: `noisereduce>=3.0` with `stationary=False`

**Rationale**:
- Works on numpy arrays of any length (including 2s chunks)
- `stationary=False` mode uses per-chunk noise estimation via short-time statistics — no pre-recorded silence required
- Pure Python + numpy: no native extension to compile, no CUDA dependency
- `prop_decrease=0.75` (recommended default): reduces noise 75% rather than eliminating it completely, preserving speech naturalness
- Overhead: ~5-15ms for a 2s chunk on a modern CPU — well within the 500ms budget

**Alternatives considered**:

| Alternative | Verdict | Reason Rejected |
|---|---|---|
| `webrtcvad` | Rejected | VAD only — classifies frames as speech/silence but cannot attenuate noise during speech frames. A noisy speech frame passes through unmodified. |
| `DeepFilterNet` | Rejected | ML model download (~50MB), GPU recommended, complex install. Too heavy for hackathon constraint (Principle V). |
| `RNNoise` (`rnnoise-python`) | Rejected | Requires native C extension, complex wheel, poor macOS support on M1/M2. Ops risk on demo day. |
| `scipy.signal` + manual spectral subtraction | Rejected | ~100 lines of DSP code for worse results than a dedicated library. noisereduce IS scipy-based spectral subtraction — use the library. |
| Browser-only (WebRTC constraints) | Insufficient alone | Handles steady-state hum but not dynamic audience noise during speech. Backend layer needed for claps/coughs/voices. |

---

## PCM ↔ numpy Conversion

### Decision: Direct numpy frombuffer / tobytes — no soundfile needed

**Rationale**: The audio format is fully known: 16-bit signed integer, mono, 16kHz, little-endian. No audio file container parsing is needed.

```python
# PCM bytes → float32 for noisereduce
audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
# float32 → PCM bytes after reduction
result = (reduced * 32768.0).clip(-32768, 32767).astype(np.int16).tobytes()
```

**Clipping**: Spectral subtraction can produce values slightly outside [-1.0, 1.0]; `np.clip` before int16 cast prevents overflow.

---

## Integration Point in AudioAgent

### Decision: Inject noise reduction at the top of `push_chunk`, before `_transcribe`

**Rationale**: `push_chunk` (line 106) is the single entry point for all audio data. The `DEMO_MODE=replay` early-return is already at the top (lines 107-116), so injecting after the replay check means:
1. Demo mode bypasses noise reduction (FR-006 ✅)
2. The `_transcribe` call and everything downstream receives cleaned PCM with no code changes
3. Exception in noise reduction → catch → log → pass raw `pcm_bytes` to `_transcribe` (FR-005 ✅)

**Proposed injection (pseudocode)**:
```python
async def push_chunk(self, pcm_bytes: bytes) -> None:
    if get_settings().demo_replay:
        ...  # existing replay path unchanged

    # NEW: attempt noise reduction; fall back to raw on any error
    pcm_bytes = apply_noise_reduction(pcm_bytes)

    chunk_dur_ms = ...  # rest of existing code unchanged
```

---

## Frontend: WebRTC Audio Constraints

### Decision: Add `noiseSuppression`, `echoCancellation`, `autoGainControl` to `getUserMedia`

**Integration point**: `capture.ts:54` — `getUserMedia({ audio: true })` → `getUserMedia({ audio: { noiseSuppression: true, echoCancellation: true, autoGainControl: true } })`

**Fallback**: If the browser rejects the enriched constraints (rare, old Safari), catch and retry with `{ audio: true }`. This preserves the existing behavior rather than blocking the session.

**Why these three**:
- `noiseSuppression`: browser-side spectral filter, handles steady-state ambient noise (HVAC, road noise)
- `echoCancellation`: suppresses room echo/reverb that confuses STT
- `autoGainControl`: normalizes gain so presenter doesn't need to position mic precisely

**AudioContext sample rate**: Already fixed at 16kHz (`ctx = new AudioContextCtor({ sampleRate: 16000 })`). Constraints don't affect sample rate.

---

## Test Strategy

### Unit tests for `noise_reduction.py`

1. **Happy path**: synthetic PCM with added white noise → verify output differs from input (noise reduced)
2. **Silence input**: all-zero PCM → output should also be near-zero (no artifacts)
3. **Exception safety**: pass non-PCM bytes → `apply_noise_reduction` must return input unchanged, not raise
4. **Short chunk**: <0.5s worth of samples → must not crash (noisereduce handles short inputs)

No integration tests required — the STT path already has `test_audio_stt.py` coverage.
