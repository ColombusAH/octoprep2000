# Contracts: Hebrew & RTL Support

## `POST /sessions`

Existing endpoint (`packages/backend/routers/sessions.py::create_session`). Gains two optional request
fields; the response shape is unchanged.

### Request

```json
{
  "topic": "string",
  "topic_context": "string | null",
  "speech_language": "en|he",
  "deck_language": "en|he"
}
```

- `speech_language` (optional, default `"en"`): the presenter's explicit declaration of which
  language they will speak (FR-008). Stored on `sessions.speech_language`; never inferred.
- `deck_language` (optional, default `"en"`): the presenter's explicit declaration of which language
  the uploaded deck is in (FR-009), independent of `speech_language`. Stored on
  `sessions.deck_language`.

### Response (201) — unchanged

```json
{ "session_id": "uuid", "access_token": "uuid" }
```

## `GET /sessions/{session_id}/report`

Existing endpoint (`packages/backend/routers/sessions.py::get_report`). Gains one optional query
parameter and two additive response fields; no existing field changes shape or meaning.

### Request

```
GET /sessions/{session_id}/report?lang=en|he
```

- `lang` (optional): desired display language. Omit to get the session's `speech_language` default
  (FR-010).
- Auth unchanged: `require_report_access` (owner `access_token` or report `share_token`), per
  Constitution Principle III. Language selection MUST NOT bypass or alter this check.

### Response (200)

```json
{
  "session_id": "uuid",
  "overall_score": 0,
  "voice_score": 0,
  "body_score": 0,
  "slide_score": 0,
  "content_score": 0,
  "insights": [
    {
      "category": "voice",
      "type": "IMPROVEMENT",
      "message": "string — already resolved to the response's `language`",
      "timestamps": [0],
      "slides": [0]
    }
  ],
  "mentor_unlocked": true,
  "generated_at": "iso-8601",
  "language": "en|he",
  "speech_language": "en|he"
}
```

New fields:

- `language`: the language `insights[].message` is actually rendered in for this response.
- `speech_language`: the session's declared speech language (FR-008) — always present, defaults to
  `"en"`.

Unchanged fields keep their existing shape exactly (`overall_score`, `voice_score`, `body_score`,
`slide_score`, `content_score`, `mentor_unlocked`, `generated_at`, and the existing
`insights[].category/type/timestamps/slides`).

### Behavior

1. If `lang` is omitted, resolve to `speech_language`.
2. If `lang` matches a language already cached on every insight (`message_en`/`message_he` populated —
   see data-model.md), respond immediately from the stored row (no LLM call; <2s, satisfies SC-003).
3. If `lang` requests the language *other than* `speech_language` and one or more LLM-derived insights
   are missing that language's text, translate only those findings in a single batched call, persist
   the result back onto the `reports` row, then respond. This is the one-time cost noted in
   research.md Decision 3.
4. If step 3's translation call fails, respond with the original-language text for the affected
   insights; to avoid mislabeling untranslated text, the endpoint returns `language` equal to whatever
   language is actually present (i.e., falls back to `speech_language`) rather than claiming the
   requested language was honored. This is the demo-safe degradation required by CAR-004.
5. Embedded quotes inside any insight `message` remain in their original spoken/written language with
   a short label, in both `message_en` and `message_he` — never machine-translated (FR-010).

## Out of scope for these contracts

- No change to `GET /sessions/{id}`, `POST /sessions/{id}/end`, or `POST /sessions/{id}/report/share`.
- No new WebSocket message type — `TranscriptPayload` is unchanged (Decision 1, research.md: language
  is declared at session creation, not detected from transcript chunks).
