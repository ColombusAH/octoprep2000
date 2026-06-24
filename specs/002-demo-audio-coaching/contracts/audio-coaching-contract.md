# Audio Coaching Contracts

## Browser Audio Input WebSocket

**Endpoint**: `WS /audio-stream?session_id={uuid}&token={access_token}`

**Direction**: Browser to backend.

**Authentication**: Capability token must match `sessions.access_token` for `session_id`.

**Session state**: Server should accept audio only while the session is `ACTIVE`.

**Message format**: Binary frame containing raw PCM samples.

**PCM format**:

- Sample rate: `16000` Hz.
- Channels: `1` mono.
- Sample format: signed 16-bit little-endian PCM.
- Chunk duration: default `2` seconds, from public config `audio_chunk_seconds`.
- Expected full chunk byte length: `16000 * 2 seconds * 2 bytes = 64000` bytes.
- Final partial chunks are allowed if implementation flushes remaining samples at stop.

**Server behavior**:

- Wrap PCM bytes in a WAV container before calling STT.
- Ignore empty/silence/no-text STT results.
- Persist valid transcript segments through `Orchestrator.on_transcript` only.
- Persist audio warnings through `Orchestrator.on_audio_warning` only.
- Do not block session completion on STT errors.

**Failure behavior**:

- Invalid token: WebSocket closes with code `4003`.
- Missing/ended session: close or ignore without persisting audio evidence.
- Provider failure: log and continue; final report must remain reachable.

## TranscriptPayload

**Producer**: `AudioAgent`

**Consumer**: `Orchestrator.on_transcript`

```json
{
  "session_id": "uuid",
  "start_ms": 0,
  "end_ms": 2000,
  "text": "Hi everyone, today um I want to talk about React 19 new features.",
  "filler_flags": ["um"]
}
```

**Validation**:

- `session_id` is required.
- `start_ms >= 0`.
- `end_ms >= start_ms`.
- `text` must contain recognizable words.
- `filler_flags` defaults to `[]` and should be normalized lowercase.

## AudioWarningPayload

**Producer**: `AudioAgent`

**Consumer**: `Orchestrator.on_audio_warning`

```json
{
  "session_id": "uuid",
  "timestamp_ms": 1500,
  "event_type": "FILLER_WORDS",
  "severity": "LOW",
  "message": "Filler word: um",
  "metadata": null
}
```

**Allowed `event_type` values**:

- `FILLER_WORDS`
- `PACING_TOO_FAST`
- `PACING_TOO_SLOW`
- `STALE_SLIDE` (existing shared type; not introduced by this feature)

**Allowed `severity` values**:

- `LOW`
- `MEDIUM`
- `HIGH`

**Validation**:

- `timestamp_ms >= 0`.
- `message` must be clear text suitable for UI display.
- Repeated warnings should be throttled for live feedback.
- Duplicate persisted warnings should be prevented by natural key `(session_id, timestamp_ms, event_type, message)` or equivalent repository logic.

**Optional contract change**:

If backend provider/capture failures need persisted report evidence, add an explicit warning type such as `AUDIO_UNAVAILABLE` to both `packages/backend/agents/schemas.py` and `packages/shared-types/src/index.ts`. Skip this unless implementation needs a persisted backend failure event; frontend local capture messages already cover microphone permission/device loss.

## FeedbackEvent

**Endpoint**: `WS /realtime-feedback?session_id={uuid}&token={access_token}`

**Direction**: Backend to browser.

```json
{
  "type": "PACING_TOO_FAST",
  "severity": "MEDIUM",
  "message": "Speaking too fast (185 WPM)",
  "timestamp_ms": 30000,
  "session_id": "uuid"
}
```

**Session events**:

- `REPORT_READY`: Browser navigates to `/session/:id/report`.
- `FALLBACK_ACTIVATED`: Browser shows a non-blocking clear-text warning.

**Live warning behavior**:

- Browser may hide audio warnings unless live feedback is enabled.
- Server should still record transcript evidence and final-report findings regardless of the live feedback toggle.
- Warning text must not rely on color alone.

## ReportData Voice Contract

**Endpoint**: `GET /sessions/{session_id}/report`

**Relevant response fields**:

```json
{
  "session_id": "uuid",
  "voice_score": 84.0,
  "insights": [
    {
      "category": "voice",
      "type": "IMPROVEMENT",
      "message": "Filler words: 'um' (1x). Try pausing instead.",
      "timestamps": [0],
      "slides": []
    }
  ]
}
```

**Validation**:

- `voice_score` remains numeric `0..100` for compatibility.
- Voice insights must be generated from persisted transcript and warning evidence.
- No usable speech must produce a clear `voice` insight instead of blocking report retrieval.
- Duplicate warning rows must not produce visibly repeated report rows.

## Demo Replay Fixture Contract

**File**: `packages/backend/fixtures/audio_events.json`

**Transcript fixture**:

```json
{
  "kind": "transcript",
  "start_ms": 0,
  "end_ms": 2000,
  "text": "Hi everyone, today um I want to talk about React 19 new features.",
  "filler_flags": ["um"]
}
```

**Warning fixture**:

```json
{
  "kind": "warning",
  "timestamp_ms": 30000,
  "event_type": "PACING_TOO_FAST",
  "severity": "MEDIUM",
  "message": "Speaking too fast (185 WPM)"
}
```

**Validation**:

- Fixture rows must be copied before parsing to avoid mutating cached source data.
- Replay events are scoped to the active `session_id` at materialization time.
- Replay events are emitted once per session in `DEMO_MODE=replay`.
