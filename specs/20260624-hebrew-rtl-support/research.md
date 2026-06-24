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

## Decision 2: Deterministic-template localization — branch cleanly on the declared speech language

**Decision**: Add a Hebrew hesitation/filler word set (e.g., "אה", "אהמ", "כאילו", "סתם", "בעצם") to
`audio_agent.py` as a second `FILLERS_HE` set alongside the existing `FILLERS` (English), and select
which regex to apply per chunk based on `Session.speech_language` (now known with certainty from
Decision 1, not inferred) rather than merging both into one always-on regex.

**Update after merging `origin/main`**: the agent-direct-persistence merge brought in a second,
identically-shaped bug surface — `pptx_agent.py` now has its own deterministic, English-only fallback
content: `_FACTOR_FIX_TEMPLATES` (12 entries) plus several f-string `description`/`suggested_fix`
strings inside `_supplement_from_metadata`, used whenever the LLM under-covers a playbook factor or
leaves `suggested_fix` empty. Exactly like the filler lexicon, this text is written permanently to
`slide_analyses` at upload time — if left English-only, a Hebrew-spoken session's *default* report
view would silently mix Hebrew (LLM-written) and English (deterministic-fallback) slide insights.
This is folded into the same decision: `_FACTOR_FIX_TEMPLATES` and the `_supplement_from_metadata`
f-strings get a Hebrew variant set, selected by the deck's resolved output language (the same
`speech_language` the LLM prompt is instructed to write in — see Decision 3), authored once as a
bounded, finite list (12 factor templates + ~8 deterministic descriptions), the same shape of work as
the filler lexicon. This guarantees `slide_analyses.description`/`suggested_fix` is always already in
`speech_language` regardless of whether the LLM or the deterministic fallback produced it, so
`ReportAgent` never has to detect and re-normalize a stray English string inside a Hebrew report.

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

## Decision 3: Bilingual report content — generate in the declared speech language, translate eagerly in the same write

**Decision** (revised after merging `origin/main` — see "Superseded" below): At session end,
`ReportAgent` generates insights in the presenter's **declared speech language** exactly as before
(`ContentAnalysisAgent` and `PPTXAgent`'s prompts explicitly instruct the model to write
`message`/`description`/`suggested_fix` text in that language; `PPTXAgent`'s prompt is given the
deck's declared `deck_language` as interpretive context — plain Unicode text extraction via
`python-pptx` already handles Hebrew with no OCR/Vision change, so FR-009's deck-language requirement
is materially cheaper than it first looked). Deterministic, Python-templated insights (voice
filler/pacing counts, body-event counts, and — per Decision 2 — the PPTX fallback templates) are
rendered directly in both languages, since they involve no LLM call. Then, still inside the same
`ReportAgent.generate()` call, **one additional batched LLM call** translates only the LLM-derived
findings (content findings + slide descriptions/fixes) into the *other* language, and `ReportAgent`
writes both `message_en` and `message_he` into `reports.insights` as part of its single, existing
`insert_report` write (no separate write, no later mutation of the row). Quotes embedded in any
finding (`context_quote`) are preserved verbatim in their original language with a small label, never
machine-translated (FR-010). `GET /sessions/{id}/report?lang=` (Decision 4) becomes a pure read — it
picks `message_en` or `message_he`, nothing is generated or written at request time.

**Rationale**: This decision was originally lazy-and-cached (see "Superseded" below), but merging
`origin/main`'s Constitution v2.0.0 amendment (Principle II: one writer per role-scoped table) changed
the calculus. A lazy design has `GET /report` translate-and-write-back on first non-default-language
view — exactly the "a handler writes a table it doesn't own" pattern the new Principle II forbids;
`reports` is `ReportAgent`'s table. There's no clean way to route that write back through `ReportAgent`
from a GET handler without it being worse than just generating both languages at write time. Separately,
the original ≤60s-budget argument against eager generation overstated the risk: slide findings are
already generated off the post-session critical path (PPTXAgent runs at *upload* time, not at session
end), and the deterministic insights are free regardless. The only LLM call already on the 60s path is
`ContentAnalysisAgent`; adding one more bounded, batched translation call (a handful of short finding
strings, not the full transcript) to that same path is a small, well-understood cost — and the user has
asked, more than once, for the report-language choice to be a first-class, always-available decision,
not a rare edge case optimized away. A failure in the translation call falls back to writing
`message_he = message_en` (or vice versa) with a label, so report generation still completes
(Principle IV) — it degrades the *translation*, not the report.

**Alternatives considered**:
- *Lazy, translate-and-cache on first `GET /report?lang=` request (original decision)*: Superseded —
  conflicts with the post-merge Principle II ("one writer per table"; a GET handler writing back to
  `reports` is exactly the pattern that rule exists to prevent), and optimizes for "the user rarely
  toggles," which this feature's own requirements contradict.
- *Translate on every toggle, no caching*: Rejected — wastes a full LLM call on every view after the
  first, and risks visible latency/failure on demo day for something that doesn't need to be live.

**Consequence for spec interpretation**: SC-003 ("switch in under 2 seconds") now holds unconditionally
— there is no first-toggle exception, since both languages exist from the moment the report is
generated. This is a strict improvement over the superseded lazy design's documented caveat.

## Decision 4: `GET /sessions/{id}/report` contract — single `?lang` query param, pure read

**Decision**: The endpoint gains an optional `lang=en|he` query parameter. The response shape is
unchanged except for two additions: `language` (the language actually returned) and
`speech_language` (the session's declared speech language, FR-008) — `insights[].message` is a plain
string, picked from the already-bilingual `message_en`/`message_he` stored by `ReportAgent` (Decision
3). The frontend never sees the internal bilingual JSONB shape, and the endpoint performs no write and
no LLM call — it is a pure read regardless of which language is requested.

**Rationale**: Keeps `packages/shared-types/src/index.ts` and `ScoreCard.tsx` changes minimal — they
gain a couple of optional top-level fields instead of restructuring `Insight.message` into an object
that every consumer would need to unwrap. Because Decision 3 now writes both languages at generation
time, this handler has no persistence concern at all — it cleanly stays a read-only router action
under any ownership rule.

**Alternatives considered**:
- *Expose both languages in every response, let the frontend pick*: Rejected — pushes a trivial
  field-pick onto the client for no benefit, and complicates the `share_token` read path for no
  reason.

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
