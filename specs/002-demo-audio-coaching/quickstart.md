# Quickstart Validation: Demo Audio Coaching

## Prerequisites

- Node 20+ and pnpm 9+.
- Python 3.11+ and uv.
- Docker available for PostgreSQL.
- `.env` exists at repo root.
- For live STT: set `LITELLM_API_KEY`; optionally set `ELEVENLABS_API_KEY` for direct Scribe fallback.
- For fallback demo validation: set `DEMO_MODE=replay`.

## Setup

```bash
make install
make db-up
make db-migrate
```

Run the app:

```bash
make dev
```

Backend: `http://localhost:8000`

Frontend: `http://localhost:3000`

## Validation Scenario 1: Live Audio Transcript and Report

1. Ensure `.env` does not set `DEMO_MODE=replay`.
2. Ensure `LITELLM_API_KEY` is configured.
3. Open `http://localhost:3000/start`.
4. Create a session and open the practice page.
5. Grant microphone permission.
6. Start recording and speak for 30-60 seconds using a script that includes `um` or `uh` and one deliberately fast 10-second segment.
7. End the session.

Expected outcome:

- The browser reaches `/session/:id/report`.
- The report loads within 60 seconds.
- Voice feedback includes at least one transcript-backed filler or pacing insight.
- Insight timestamps correspond to moments in the rehearsal.

## Validation Scenario 2: Replay Fallback Demo Path

1. Set `DEMO_MODE=replay` in `.env`.
2. Restart backend/frontend.
3. Start a session and record long enough to send multiple audio chunks.
4. End the session and open the report.

Expected outcome:

- Prepared transcript/warning evidence appears in the report.
- Repeated audio chunks do not create visibly duplicated transcript or warning rows.
- The report remains coherent and demo-ready.

## Validation Scenario 3: Microphone Permission Failure

1. Open a new session page.
2. Deny microphone permission while allowing camera if desired.
3. Start and end the session.

Expected outcome:

- The UI shows a clear text warning such as microphone unavailable or permission denied.
- The user can still end the session.
- The report route remains reachable.
- If no usable speech exists, the report communicates insufficient/no audio rather than crashing or blocking.

## Validation Scenario 4: Live Feedback Toggle

1. Start a session with live feedback disabled.
2. Say `um` or `uh` during recording.
3. Confirm no distracting live warning is shown.
4. Repeat with live feedback enabled.

Expected outcome:

- Disabled live feedback does not suppress final report evidence.
- Enabled live feedback shows non-blocking warning toasts.
- Repeated warnings are throttled enough not to spam the presenter.

## Validation Scenario 5: WebSocket Session Isolation

Run backend tests covering bad-token rejection and add/verify authorized audio-stream tests with fake STT.

```bash
cd packages/backend && uv run pytest tests/test_ws_auth.py
```

Expected outcome:

- `/audio-stream`, `/video-stream`, and `/realtime-feedback` reject bad tokens with close code `4003`.
- Authorized audio writes are scoped to the correct session.
- Ended sessions do not accept new persisted audio evidence.

## Validation Scenario 6: Deterministic Backend Unit Tests

Run focused backend tests while implementing this feature:

```bash
cd packages/backend && uv run pytest tests/test_wav_header.py tests/test_report_dedup.py
```

Additional tests expected from implementation:

- Filler matching detects `um`/`uh` and does not match words like `umbrella`.
- Ambiguous `like` behavior matches the approved policy.
- Pacing warnings require sustained evidence and debounce repeated alerts.
- Replay fixture loading does not mutate cached JSON rows.
- Replay audio events are emitted once per session.
- Mocked STT fallback covers gateway-first, direct-first, empty text, and provider error paths.

## Full Validation

Run full checks before declaring the feature complete:

```bash
make lint
make test
```

If `make test` fails because a package lacks a `test` script, run the backend pytest and frontend typecheck commands directly and document the limitation in the implementation report.
