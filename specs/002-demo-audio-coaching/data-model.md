# Phase 1 Data Model: Demo Audio Coaching

## Entity: Practice Session

Represents one rehearsal owned by one presenter.

**Current storage**: `sessions`

**Fields**:

- `session_id`: UUID primary key.
- `access_token`: UUID capability token for session-owner actions and WebSockets.
- `topic`: Required presentation topic.
- `topic_context`: Optional context.
- `status`: `ACTIVE`, `ENDED`, or `REPORT_READY`.
- `pptx_ready`: Whether deck analysis completed.
- `slides_raw_text`: Optional extracted slide text.
- `started_at`: Server timestamp.
- `ended_at`: Optional server timestamp.

**Relationships**:

- Has many `Transcript Segment` rows.
- Has many `Voice Warning` rows.
- Has one `Voice Report Outcome` row.
- Also relates to video events and slide analyses outside this audio feature.

**Validation rules**:

- `session_id` and `access_token` are required for `/audio-stream` and `/realtime-feedback`.
- Audio chunks must only be accepted for the matching session token.
- New audio writes should be rejected or ignored once status is no longer `ACTIVE`.

**State transitions**:

```text
ACTIVE -> ENDED -> REPORT_READY
```

`DEMO_MODE=replay` must not create cross-session shared state; replay evidence is scoped to the current `session_id`.

## Entity: Transcript Segment

Timestamped recognized speech evidence for a practice session.

**Current storage**: `transcript_entries`

**Fields**:

- `id`: Integer primary key.
- `session_id`: UUID foreign key to `sessions.session_id`.
- `start_ms`: Segment start offset from session start, non-negative.
- `end_ms`: Segment end offset from session start, non-negative and greater than or equal to `start_ms`.
- `text`: Non-empty recognized speech text.
- `filler_flags`: Optional list of filler words found in `text`.

**Relationships**:

- Belongs to one `Practice Session`.
- Feeds `Voice Warning` generation and final `Voice Report Outcome` scoring.

**Validation rules**:

- Do not persist segments for silence, noise, or empty STT output.
- Filler flags must be derived from text and normalized to lowercase.
- Minimum required fillers for this feature: `um`, `uh`.
- Ambiguous fillers such as `like` should be conservative to avoid over-penalizing meaningful usage.
- Replay/live dedup natural key: `(session_id, start_ms, end_ms, text)`.

## Entity: Voice Warning

Timestamped coaching event generated from audio capture or analysis.

**Current storage**: `audio_warnings`

**Fields**:

- `id`: Integer primary key.
- `session_id`: UUID foreign key to `sessions.session_id`.
- `timestamp_ms`: Event timestamp offset from session start, non-negative.
- `event_type`: One of `FILLER_WORDS`, `PACING_TOO_FAST`, `PACING_TOO_SLOW`, or existing non-audio-adjacent `STALE_SLIDE`.
- `severity`: `LOW`, `MEDIUM`, or `HIGH`.
- `message`: User-understandable warning text.
- `metadata`: Available on the Pydantic payload but not currently persisted.

**Relationships**:

- Belongs to one `Practice Session`.
- May be broadcast as a live feedback `FeedbackEvent`.
- Feeds voice scoring in the final `Voice Report Outcome`.

**Validation rules**:

- Warning timestamps must be non-negative and session-scoped.
- Filler warnings should be throttled for live display and deduplicated for persistence.
- Pacing warnings should require sustained evidence, not a single tiny chunk.
- Replay/live dedup natural key: `(session_id, timestamp_ms, event_type, message)`.

## Entity: Voice Report Outcome

Final report content summarizing audio-coaching feedback.

**Current storage**: `reports` plus `ReportPayload.insights`

**Fields**:

- `session_id`: UUID foreign key to `sessions.session_id`.
- `voice_score`: Numeric score, current contract requires `0..100`.
- `insights`: JSON list of report insights, including voice findings with `category="voice"`.
- `generated_at`: Server timestamp.
- `overall_score`, `body_score`, `slide_score`, `content_score`, and `mentor_unlocked`: Existing report contract fields.

**Relationships**:

- Belongs to one `Practice Session`.
- Aggregates `Transcript Segment` and `Voice Warning` rows.

**Validation rules**:

- If transcript evidence exists, report voice insights must include transcript-backed filler and pacing findings when detected.
- If no usable audio exists, report must include a clear no-audio or insufficient-audio voice insight and remain reachable.
- Duplicate warnings must be consolidated into one insight with timestamp arrays.
- Report generation should complete within 60 seconds after session end.

## Entity: Demo Fallback Audio Event

Prepared event used only when demo replay is explicitly enabled.

**Current storage**: `packages/backend/fixtures/audio_events.json`

**Fields**:

- `kind`: `transcript` or `warning`.
- Transcript fields: `start_ms`, `end_ms`, `text`, `filler_flags`.
- Warning fields: `timestamp_ms`, `event_type`, `severity`, `message`.

**Relationships**:

- Materializes as `Transcript Segment` or `Voice Warning` rows for the active `Practice Session`.

**Validation rules**:

- Only used when `DEMO_MODE=replay` is active.
- Must be emitted at most once per session.
- Fixture source data must not be mutated while loaded from cache.
- Output must not duplicate visible transcript or warning rows within a single completed session.

## Entity: Feedback Event

Live outbound WebSocket event shown by the dashboard when live feedback is enabled.

**Current transport**: `/realtime-feedback` WebSocket; shared TypeScript `FeedbackEvent`

**Fields**:

- `type`: Audio warning type or session status event such as `REPORT_READY`.
- `severity`: Optional `LOW`, `MEDIUM`, or `HIGH`.
- `message`: Optional clear user-facing text.
- `timestamp_ms`: Optional session timestamp.
- `session_id`: Optional UUID string.

**Validation rules**:

- Feedback socket requires `session_id` and `access_token`.
- User-facing warnings must use text, not color alone.
- Live audio warnings should be non-blocking and throttled.
