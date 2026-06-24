# Data Model: Audio Noise Reduction Pipeline

**Feature**: 006-audio-noise-reduction
**Date**: 2026-06-24

## No New Database Entities

This feature introduces zero new database tables, columns, or migrations. Noise reduction is a stateless transformation applied to PCM bytes in memory before they reach ElevenLabs. The output (cleaned PCM) is consumed immediately by the STT call and discarded. No intermediate audio is persisted.

All existing tables (`transcript_entries`, `audio_warnings`, `sessions`) are unchanged.

---

## In-Memory Entities (Transient, Not Persisted)

### AudioChunk (transient)

Represents a single 2-second window of raw or noise-reduced PCM.

| Attribute | Type | Description |
|---|---|---|
| raw_bytes | `bytes` | Raw PCM 16-bit mono 16kHz from browser (64,000 bytes per 2s chunk) |
| clean_bytes | `bytes` | PCM bytes after noise reduction (same length as raw_bytes) |
| sample_rate | int | Always 16000 (Hz) |
| channels | int | Always 1 (mono) |
| bit_depth | int | Always 16 |

**Lifecycle**: Created on WebSocket receive, reduced in `push_chunk`, passed to `_transcribe`, then garbage-collected. Never stored.

---

### NoiseProfile (transient, implicit in noisereduce)

`noisereduce` with `stationary=False` maintains no explicit noise profile object. It estimates the noise spectrum internally per call from the spectral content of each chunk. No state is held between chunks in `noise_reduction.py`.

**Consequence**: `apply_noise_reduction` is a pure function — same input always produces the same output. This simplifies testing and means no session-level cleanup is needed.

---

## Config Additions

One new optional setting in `config.py` (via `Settings`):

| Setting | Type | Default | Description |
|---|---|---|---|
| `noise_reduction_enabled` | `bool` | `True` | Feature flag to disable noise reduction without code change. Useful if it causes performance issues on demo day. |

This setting is read by `apply_noise_reduction()`. If `False`, the function returns `pcm_bytes` unchanged immediately.

No `.env.example` entry required (default is `True`; silence = enabled).
