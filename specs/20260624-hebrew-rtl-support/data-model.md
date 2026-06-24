# Data Model: Hebrew & RTL Support

## Modified Entities

### Session (`packages/backend/db/models.py::Session`, table `sessions`)

New columns, both written once at session creation from the request body — never inferred or
overwritten afterward:

| Field | Type | Notes |
|---|---|---|
| `speech_language` | `String(8)`, not null, default `"en"` | `"en"` or `"he"`. The presenter's explicit declaration of which language they will speak, made on the `start` screen before the rehearsal begins (FR-008). Drives the STT language hint, the filler-word lexicon (Decision 2, research.md), and the report's default display language (FR-010). |
| `deck_language` | `String(8)`, not null, default `"en"` | `"en"` or `"he"`. The presenter's explicit declaration of which language the uploaded deck is in (FR-009), independent of `speech_language`. Given to `PPTXAgent` as prompt context so it correctly interprets the extracted slide text. |

Both default to `"en"`, so an existing/unmodified session-creation request behaves exactly as before
this feature (FR-006, no regression). No detection logic, confidence threshold, or write-once-after-
the-fact semantics are needed — both values are simply part of the validated request at creation time.

No other column changes. `slides_raw_text` is unaffected — slide text extraction (`python-pptx`)
already handles Hebrew Unicode text natively; only the LLM prompt context changes (Decision 3).

### Report (`packages/backend/db/models.py::Report`, table `reports`)

No new column. The existing `insights` JSONB column's *internal* shape changes (see "Insight (internal
storage shape)" below); this is a data-shape change within an already-flexible JSONB field, not a
schema migration.

## New Internal Shape (not a DB schema change)

### Insight (internal storage shape, inside `reports.insights` JSONB)

Replaces the single `message: str` field used today:

| Field | Type | Notes |
|---|---|---|
| `category` | `"voice" \| "body" \| "slide" \| "content"` | Unchanged. |
| `type` | `"STRENGTH" \| "IMPROVEMENT"` | Unchanged. |
| `message_en` | `string` | Always present. For deterministic (voice/body) insights, rendered directly in English. For LLM-derived (content/slide) insights, this is whichever language the LLM call actually produced — i.e. equals the generated text when `speech_language` is `"en"`, or is filled in by the lazy-translate path (Decision 3) once an English view has been requested for a Hebrew-spoken session. |
| `message_he` | `string \| null` | Same rule, mirrored: present once generated (deterministic, or LLM-generated when `speech_language` is `"he"`) or translated-and-cached; `null` until the Hebrew view has been requested for an insight that originated in English. |
| `timestamps` | `list[int]` | Unchanged. |
| `slides` | `list[int]` | Unchanged. |

Embedded quotes (e.g., `context_quote` text folded into a content finding's message) are never
translated — they appear verbatim, identically, inside both `message_en` and `message_he`, with a
short inline language label when the surrounding sentence is in the other language (FR-010).

This shape is **internal only**. The `GET /sessions/{id}/report` response continues to expose a single
resolved `message: string` per insight (see `contracts/report-api.md`) — external consumers
(frontend, `share_token` viewers) never see `message_en`/`message_he` directly.

## Modified Contracts (Pydantic, `packages/backend/agents/schemas.py`)

### CreateSessionBody

New required-with-default fields:

| Field | Type | Notes |
|---|---|---|
| `speech_language` | `Literal["en", "he"]`, default `"en"` | Presenter's explicit speech-language declaration (FR-008). |
| `deck_language` | `Literal["en", "he"]`, default `"en"` | Presenter's explicit deck-language declaration (FR-009). |

`create_session` writes both directly onto the new `Session` columns above — no agent or
Orchestrator round-trip needed for this part, since it's part of the original validated request, not
something discovered mid-session.

### Insight (Pydantic)

`message: str` → `message_en: str`, `message_he: str | None` (mirrors the internal JSONB shape above).
`ReportAgent` continues to build these in-memory exactly as it does today for the deterministic
categories; LLM-derived categories populate only the `speech_language` field at generation time
(the prompt now explicitly instructs the model to write in that language), leaving the other `None`
until the lazy-translate path fills it in.

## Unaffected Entities / Contracts

- **TranscriptPayload**: no new field. Language detection is no longer performed at all (Decision 1,
  research.md) — `speech_language` is known from session creation, not inferred from transcribed text.
- **TranscriptEntry**: no new column. Per-segment language tagging isn't needed — the speech language
  is a single, presenter-declared, session-level value, and the filler lexicon now branches cleanly on
  it (Decision 2, research.md) rather than needing per-segment disambiguation.
- **VideoEvent**, **AudioWarning**, **SlideAnalysis**: unchanged. Body/video event types are
  enum-driven, not freeform text requiring translation.

## Runtime wiring (`packages/backend/runtime.py`)

`RuntimeRegistry` loads the session row (already does, to construct per-session agents) and passes
`speech_language` into the `AudioAgent` constructor, so it's available for both the STT language hint
and the filler-lexicon selection without `AudioAgent` needing its own DB read.

## New Frontend-Facing Shape (`packages/shared-types/src/index.ts::ReportData`)

Additive only — no breaking change to existing consumers:

| Field | Type | Notes |
|---|---|---|
| `language` | `"en" \| "he"` | The language the returned `insights[].message` strings are actually in (resolves the `?lang` query param against what's available). |
| `speech_language` | `"en" \| "he"` | The session's declared speech language — the report's default `language` when no `?lang` is given (FR-010). |

`Insight.message` stays a single resolved `string` on the wire (Decision 4, research.md) — the
frontend never needs to know about `message_en`/`message_he`.

### New Frontend-Facing Shape (`CreateSessionResponse` / session-creation request)

The `start` screen's create-session call gains two form fields (`speech_language`, `deck_language`,
each a simple two-option control defaulting to "English") sent in the existing `POST /sessions` body
alongside `topic`/`topic_context`. No new endpoint.

## Persisted UI Preference (not a DB entity)

**Interface Language Preference** (FR-011, US3/P3): a small cookie (e.g. `octoprep_ui_lang=he|en`),
read by the TanStack Start root loader so `<html lang dir>` is correct on first server-rendered paint,
with a Settings-page control to change it. Not stored in PostgreSQL — it's a per-browser UI
preference, independent of any session's `speech_language`/`deck_language`.
