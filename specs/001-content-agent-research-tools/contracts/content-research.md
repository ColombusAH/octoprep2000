# Contract: Content Analysis Payload (extended)

**Version**: 1.1 (backward-compatible extension)  
**Producer**: `ContentAnalysisAgent`  
**Consumer**: `ReportAgent`, `GET /sessions/{session_id}/report`

## ContentAnalysisPayload

```json
{
  "session_id": "uuid",
  "topic": "string",
  "content_score": 0.0,
  "findings": [
    {
      "type": "FACTUAL_ERROR | COVERAGE_GAP | STRENGTH",
      "message": "string",
      "context_quote": "string"
    }
  ],
  "research_status": "full | partial | skipped | not_applicable"
}
```

### Field rules

- `research_status` is optional in transport; consumers MUST default to `not_applicable` when absent.
- `findings` schema is unchanged from v1.0.
- Producers MUST NOT add findings that lack transcript grounding for `FACTUAL_ERROR` (quote required when claim is in transcript).

---

# Contract: Report API (extended)

**Endpoint**: `GET /sessions/{session_id}/report`  
**Auth**: `access_token` query param or `share_token` (unchanged)

## Response addition

```json
{
  "session_id": "uuid",
  "overall_score": 0.0,
  "voice_score": 0.0,
  "body_score": 0.0,
  "slide_score": 0.0,
  "content_score": 0.0,
  "content_research_status": "full | partial | skipped | not_applicable",
  "insights": [],
  "mentor_unlocked": false,
  "generated_at": "iso8601"
}
```

### Insight injection rules (ReportAgent)

When `content_research_status` is `partial` or `skipped`, prepend one content insight:

| status | insight.type | insight.message (example) |
|---|---|---|
| `partial` | IMPROVEMENT | Reference lookup partially available — some sources could not be reached. |
| `skipped` | IMPROVEMENT | Reference lookup unavailable — content scored from transcript only. |

When `full`, no status insight is added.

---

# Contract: Research Provider — Exa (internal)

**Module**: `agents/content_research/exa_client.py`

## Input

```python
search_articles(query: str, *, num_results: int = 5) -> list[ReferenceSnippet]
search_improvements(topic: str, *, num_results: int = 5) -> list[ReferenceSnippet]
```

## Output snippet shape

```python
ReferenceSnippet(
  source="article" | "improvement_guide",
  title=str,
  url=str,
  excerpt=str,  # max 800 chars
  provider="exa",
)
```

## Errors

- Raises `ResearchProviderError` on HTTP/timeout failures.
- Caller catches and records in `ReferenceBundle.fetch_errors`; does not propagate to session end.

---

# Contract: Research Provider — Context7 (internal)

**Module**: `agents/content_research/context7_client.py`

## Input

```python
resolve_library(library_name: str, query: str) -> str | None  # library ID e.g. /vercel/next.js
fetch_docs(library_id: str, query: str) -> list[ReferenceSnippet]
```

## Output snippet shape

```python
ReferenceSnippet(
  source="official_docs",
  title=str,
  url=str,  # optional
  excerpt=str,  # max 1200 chars
  provider="context7",
)
```

## Precedence rule

When Exa articles conflict with Context7 docs on factual claims, the content LLM prompt MUST instruct: **prefer official_docs excerpts for factual adjudication**.

---

# Contract: Topic Classifier (internal)

**Module**: `agents/content_research/classifier.py`

## Input

```python
classify_topic(topic: str, topic_context: str | None) -> TopicClassification
```

## Output

```python
TopicClassification(
  is_technical=bool,
  primary_libraries=list[str],  # max 2
  confidence=float,
  rationale=str,
)
```

## Threshold

- `is_technical` effective only when `confidence >= 0.6`.
- Below threshold → `is_technical=False`, `research_status` will be `not_applicable`.
