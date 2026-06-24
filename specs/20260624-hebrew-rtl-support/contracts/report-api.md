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

This endpoint performs a pure read — no LLM call, no write, regardless of which language is
requested. Both `message_en` and `message_he` already exist on every insight by the time the report
row exists at all (written once by `ReportAgent`, see below).

1. If `lang` is omitted, resolve to `speech_language`.
2. Pick `message_en` or `message_he` per insight, per the resolved language, and return it as
   `insights[].message`. <2s always holds (SC-003) — there is no first-request/cache-miss case.
3. Embedded quotes inside any insight `message` remain in their original spoken/written language with
   a short label, in both `message_en` and `message_he` — never machine-translated (FR-010).

## `POST /sessions/{session_id}/end` — no contract change, behavior change inside `ReportAgent`

The request/response shape is unchanged. What changes is internal to
`packages/backend/agents/report_agent.py::ReportAgent.generate()`, which this endpoint already calls:
after assembling insights in `speech_language` (LLM-derived categories) or both languages directly
(deterministic categories), it makes one additional batched translation call for the LLM-derived
findings into the *other* language, then writes both `message_en` and `message_he` as part of its
single existing `insert_report` call (research.md Decision 3). If the translation call fails, it
writes `message_he = message_en` (or vice versa) with a label rather than failing the whole report —
report generation still completes (CAR-004).

## Out of scope for these contracts

- No change to `GET /sessions/{id}` or `POST /sessions/{id}/report/share`.
- No new WebSocket message type — `TranscriptPayload` is unchanged (Decision 1, research.md: language
  is declared at session creation, not detected from transcript chunks).
