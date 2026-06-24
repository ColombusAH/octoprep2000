# Research: Hebrew & RTL Support

## Decision 1: Speech & deck language — explicit selection at session creation, not detection

**Decision**: `CreateSessionBody` gains two required-with-default fields: `speech_language: "en"|"he"`
and `deck_language: "en"|"he"` (default `"en"` for both, preserving today's behavior when a presenter
doesn't touch the new controls). The presenter picks both explicitly on the `start` screen before the
rehearsal begins. `create_session` writes both directly onto the new `sessions.speech_language` /
`sessions.deck_language` columns at creation time — no inference, heuristic, or post-hoc detection is
involved anywhere in this path. `AudioAgent` is constructed with `speech_language` (sourced from the
session row by `RuntimeRegistry`) and passes it as the `language` hint on every STT call
(`client.audio.transcriptions.create(..., language=speech_language)` / the equivalent field on the
direct ElevenLabs call), which is a standard parameter on OpenAI-Whisper-compatible transcription APIs
and ElevenLabs Scribe — forcing the decoder to the declared language instead of auto-detecting
**improves** transcription accuracy (directly supports FR-001/SC-001), as a side benefit of the
explicit-selection requirement.

**Rationale**: This reverses an earlier draft of this plan, which detected spoken language from
already-transcribed text via a Unicode-script heuristic. That heuristic is now unnecessary: the
presenter is required to declare both languages up front (FR-008, FR-009), which is simpler (Principle
V — no detection logic, no confidence threshold, no "what if the first 20 characters are ambiguous"
edge case), strictly more reliable (no risk of mis-detecting code-switched or short utterances), and
additionally improves STT accuracy itself by giving the decoder a language hint instead of guessing.

**Alternatives considered**:
- *Unicode-script detection from transcribed text (previous decision)*: Rejected — superseded by an
  explicit product requirement that presenters choose both languages themselves; detection added
  complexity (confidence thresholds, warm-up window, write-once semantics) the explicit-selection
  design simply doesn't need.
- *Auto-detect with manual override available*: Rejected for the same reason — the requirement is for
  explicit selection, not detection-with-an-escape-hatch.

## Decision 2: Hebrew filler/disfluency lexicon — branch cleanly on the declared speech language

**Decision**: Add a Hebrew hesitation/filler word set (e.g., "אה", "אהמ", "כאילו", "סתם", "בעצם") to
`audio_agent.py` as a second `FILLERS_HE` set alongside the existing `FILLERS` (English), and select
which regex to apply per chunk based on `Session.speech_language` (now known with certainty from
Decision 1, not inferred) rather than merging both into one always-on regex.

**Rationale**: Without this change, Hebrew speech still produces **zero** filler matches (the current
`FILLERS` set is English-only), which doesn't just under-report — it actively manufactures a false
"Steady pacing & low filler density" STRENGTH insight in `report_agent._score_voice`. That directly
undermines US1's value (accurate transcription must lead to *accurate coaching*, not a falsely
inflated voice score) and would ship as an invisible regression since SC-001 only measures
transcription accuracy, not analysis accuracy (captured explicitly as FR-013). Because the speech
language is now an explicit, known-upfront value (not detected mid-session), branching cleanly on it
is both simpler and more precise than merging lexicons — it avoids any chance of an English word
coincidentally matching a Hebrew filler token (or vice versa) in a single-language session.

**Alternatives considered**:
- *Merge both lexicons into one always-on regex (previous decision)*: Rejected now that the speech
  language is known with certainty before the session starts — merging was only a hedge against
  detection uncertainty, which no longer exists.
- *Leave Hebrew filler detection out of scope*: Rejected — produces a silently misleading report,
  which conflicts with the coaching product's basic credibility; captured explicitly as FR-013.

**Documented limitation**: WPM pacing thresholds (`WPM_HIGH`/`WPM_LOW`) remain a single,
English-calibrated value for both languages. Per-language speech-rate norms are a real refinement but
out of scope for this feature (see spec Assumptions).

## Decision 3: Bilingual report content — generate once in the declared speech language, translate lazily and cache

**Decision**: At session end, `ReportAgent` generates insights in the presenter's **declared speech
language only** — still a single LLM call per agent, but `ContentAnalysisAgent` and `PPTXAgent`'s
prompts now explicitly instruct the model to write `message`/`description` text in that language
(rather than always English), and `PPTXAgent`'s prompt is given the deck's declared `deck_language` as
context so it correctly interprets Hebrew slide text extracted by `python-pptx` (plain Unicode text
extraction already works for Hebrew with no OCR or Vision change — FR-009's deck-language requirement
is materially cheaper than it first looked, since slide text comes from the XML, not an image).
Deterministic, Python-templated insights (voice filler/pacing counts, body-event counts) are cheap to
render in both languages immediately, since they involve no LLM call. The **first** time
a report is requested in the non-spoken language, the backend makes one additional, batched LLM call
that translates only the LLM-derived findings (content + slide descriptions) for that report, and
persists the result back into the same `reports.insights` JSONB column so every subsequent fetch in
that language is a pure DB read. Quotes embedded in any finding (`context_quote`) are preserved
verbatim in their original language with a small label, never machine-translated (FR-010).

**Rationale**: Report generation has a constitutional ≤60s soft target (Principle IV). Eagerly
generating both languages for every report — even via a single dual-language LLM call per agent —
adds output-token latency to the critical path on every session, including the common case where a
user never toggles away from their spoken language. That cost is not justified by FR-007, which only
requires that toggling *not* re-record or re-process the rehearsal — a lazy, cached translation read
satisfies that without paying the cost up front. The one-time cost is paid only on first toggle, is a
short, low-token batched call (a handful of finding strings, not the full transcript), and a failure
falls back to showing the original-language text with a label rather than blocking the toggle
(Principle IV).

**Alternatives considered**:
- *Eager dual-language generation at session end (single call per agent, both languages in one
  schema)*: Rejected as the default — strictly worse than lazy-and-cached for the common path (adds
  latency to every report, not just the ones a user actually toggles), with no offsetting benefit
  once caching makes the lazy path's repeat-view cost zero.
- *Translate on every toggle, no caching*: Rejected — wastes a full LLM call on every view after the
  first, and risks visible latency/failure on demo day for something that doesn't need to be live.

**Consequence for spec interpretation**: SC-003 ("switch in under 2 seconds") holds for the cached
path (the common case after a report has been viewed once in each language); the very first toggle
into the non-spoken language pays one short translation call and should show a brief loading state
rather than an instant swap. This is a refinement worth flagging back to the spec owner, not a silent
deviation.

## Decision 4: `GET /sessions/{id}/report` contract — single `?lang` query param, server resolves

**Decision**: The endpoint gains an optional `lang=en|he` query parameter. The response shape is
unchanged except for two additions: `language` (the language actually returned) and
`speech_language` (the session's declared speech language, FR-008) — `insights[].message` remains a
plain string already resolved to the requested language server-side. The frontend never sees the
internal bilingual JSONB shape.

**Rationale**: Keeps `packages/shared-types/src/index.ts` and `ScoreCard.tsx` changes minimal — they
gain a couple of optional top-level fields instead of restructuring `Insight.message` into an object
that every consumer would need to unwrap. Server-side resolution is also where the lazy-translate-and-
cache logic from Decision 3 naturally lives (it already owns the DB row).

**Alternatives considered**:
- *Expose both languages in every response, let the frontend pick*: Rejected — pushes the
  translation-presence/caching logic onto the client for no benefit, and complicates the `share_token`
  read path for no reason.

## Decision 5: RTL layout and Hebrew typography

**Decision**: Use the `dir` HTML attribute plus Tailwind v4's built-in logical-property and `rtl:`
variant support (already installed — no new CSS framework or plugin needed) for layout mirroring.
Scope `dir="rtl"` first to the report view (P1/P2 — `session.$id_.report.tsx`, `ScoreCard.tsx`) since
that's the only screen required by US1/US2; extend to the persisted-cookie, root-level `<html lang
dir>` toggle for the rest of the dashboard chrome as the explicitly deferrable P3 slice (US3), read in
the root loader so server-rendered HTML has the correct direction with no flash-of-wrong-direction.
Add one new font dependency capable of Hebrew glyphs (e.g., `@fontsource/noto-sans-hebrew` or
`@fontsource-variable/noto-sans-hebrew`) applied only to Hebrew text runs; the existing display fonts
(Tektur, Chakra Petch, Space Mono, Geist) are Latin-only and would silently fall back to a generic
system font for Hebrew, breaking the Y2K/retro visual identity.

**Rationale**: Confirmed via `package.json` that Tailwind is already v4 (logical properties / `rtl:`
variants are native, no plugin needed) and that none of the four installed display fonts include
Hebrew glyphs. Settings (`settings.tsx`) currently has no working persistence layer (its toggles are
local component state only) — a cookie is the smallest mechanism that also makes the language
available to the SSR root loader, which `localStorage` cannot do without an extra client-only flash.

**Alternatives considered**:
- *Client-only `localStorage` preference*: Rejected — causes a flash of the wrong direction/language
  on every full page load until JS hydrates, which is the kind of visible regression Principle IV
  asks to avoid for user-facing UI.
- *Full i18n library (e.g., react-i18next, FormatJS)*: Rejected for this feature's scope — two
  languages, a small, enumerable set of UI strings, and a hackathon time budget make a lightweight,
  hand-rolled string map sufficient; pulling in a general-purpose i18n framework is exactly the kind
  of unjustified abstraction Principle V asks to avoid unless a concrete need proves otherwise.
