# Quickstart: Validate Hebrew & RTL Support

Prerequisites: `make install`, `make db-up`, `.env` filled in (or `DEMO_MODE=replay` for the
fixture-based path that doesn't need live API keys — see Path B).

## Path A — Live STT (requires `ELEVENLABS_API_KEY` / `LITELLM_API_KEY`)

1. `make dev` (db + backend + frontend).
2. On the `start` screen, select **Speech language: Hebrew** and **Deck language: English**, then
   upload an English-language PPTX deck and start the session.
3. During the live rehearsal, speak in Hebrew (no minimum duration needed — the language is already
   declared, not detected).
4. End the session.
5. **Expect**: `GET /sessions/{id}/report` (no `lang` param) returns `speech_language: "he"` and
   `language: "he"`, with `insights[].message` in Hebrew, including at least one Hebrew filler-word
   insight if you used common Hebrew hesitation words (FR-013).
6. Open the report in the dashboard. **Expect**: the report view renders right-to-left, score cards
   and timestamps remain legible, and status indicators are distinguishable without relying on color
   alone (CAR-005).
7. Toggle the report language control to English. **Expect**: a brief loading state on this *first*
   toggle (the one-time translation call, research.md Decision 3), then `language: "en"` with
   `insights[].message` in English and the layout mirrors back to left-to-right.
8. Toggle back to Hebrew. **Expect**: this is now instant (<2s, cached — SC-003), no loading state.
9. **Expect**: any transcript-derived quote inside an insight message is unchanged text in both
   languages — it is never machine-translated (FR-010).
10. Re-run steps 2–5 with **Speech language: English** and **Deck language: English**. **Expect**: no
    regression — `speech_language: "en"`, default report and UI stay left-to-right exactly as before
    this feature (FR-006, SC-005).
11. Re-run once more with **Speech language: English** and **Deck language: Hebrew** (a Hebrew deck,
    English speech) to confirm the two selections are genuinely independent (FR-009) — slide-specific
    insights should reflect the Hebrew deck content correctly even though the report defaults to
    English.

## Path B — `DEMO_MODE=replay` (no live API keys needed)

1. Set `DEMO_MODE=replay` in `.env`.
2. Use (or add) a Hebrew-language `audio_events.json` fixture variant under
   `packages/backend/fixtures/` so the replayed transcript contains Hebrew text (mitigates CAR-004 —
   the demo path must be rehearsable without live STT).
3. Run a session end-to-end as in Path A steps 2–9, still selecting **Speech language: Hebrew** on the
   `start` screen — replay mode bypasses the live STT call but the declared `speech_language` still
   drives the filler lexicon and report-default behavior identically.

## Backend contract check

```bash
# Default (speech-language) response
curl -s "http://localhost:8000/sessions/{id}/report?access_token={token}" | jq '.language, .speech_language'

# Explicit language override
curl -s "http://localhost:8000/sessions/{id}/report?access_token={token}&lang=en" | jq '.insights[0].message'
curl -s "http://localhost:8000/sessions/{id}/report?access_token={token}&lang=he" | jq '.insights[0].message'
```

Expect the `lang=en` and `lang=he` calls to return different `message` text for the same insight, and
the same `score` fields across all three calls (toggling language never changes scores — spec
Assumptions).

## Backend filler-detection check (FR-013)

```bash
cd packages/backend
uv run pytest tests/ -k filler -v
```

Add/confirm a unit test (alongside the existing `test_wav_header.py`-style tests) asserting that:
- a session with `speech_language="he"` and a Hebrew sentence containing a Hebrew filler word (e.g.,
  "כאילו") is detected by the Hebrew filler regex, and
- a session with `speech_language="en"` does not false-positive on Hebrew filler tokens, and vice
  versa (confirms the clean per-language branch from research.md Decision 2).

## Manual UI verification (per Constitution: frontend changes to report flow require manual desktop +
mobile verification)

- `start` screen: confirm the speech-language and deck-language controls are clearly two independent
  choices, both defaulting to English, and the form still submits correctly when left at the defaults
  (no regression for existing English-only usage).
- Desktop width: report view in Hebrew — confirm no overlapping/truncated text, share-link button and
  score cards mirror correctly.
- Mobile width: same checks, plus confirm the language toggle remains reachable and legible.
- Settings page (P3): toggle the interface-language preference, reload the page, confirm `<html lang
  dir>` matches on the very first paint (no flash of the previous direction).
