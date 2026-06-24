# Data Model: Content Agent Research Tools

**Feature**: `001-content-agent-research-tools`  
**Date**: 2026-06-24

## Overview

This feature introduces **ephemeral in-memory structures** for research and **one backward-compatible extension** to the existing content analysis payload. No new PostgreSQL tables for MVP.

---

## Extended: ContentAnalysisPayload

| Field | Type | Required | Description |
|---|---|---|---|
| `session_id` | UUID | yes | Unchanged |
| `topic` | string | yes | Unchanged — session topic evaluated |
| `content_score` | float 0–100 | yes | Unchanged |
| `findings` | list[ContentFinding] | yes | Unchanged |
| `research_status` | enum | no (default `not_applicable`) | `full`, `partial`, `skipped`, `not_applicable` |

### research_status semantics

| Value | Meaning |
|---|---|
| `not_applicable` | Non-technical topic or empty transcript; no research attempted |
| `full` | All configured research providers returned usable material |
| `partial` | Some providers succeeded; analysis used mixed reference + transcript-only reasoning |
| `skipped` | Technical topic but research disabled, timed out, or all providers failed |

### ContentFinding (unchanged)

| Field | Type | Description |
|---|---|---|
| `type` | `FACTUAL_ERROR` \| `COVERAGE_GAP` \| `STRENGTH` | Unchanged |
| `message` | string | May reference retrieved knowledge implicitly in prose |
| `context_quote` | string | Verbatim transcript excerpt; empty for coverage gaps |

---

## New (ephemeral): TopicClassification

Not persisted. Produced at start of content analysis.

| Field | Type | Description |
|---|---|---|
| `is_technical` | bool | Whether external research should run |
| `primary_libraries` | list[string] | 0–2 library/product names for Context7 (e.g. `react`, `kubernetes`) |
| `confidence` | float 0–1 | Classifier confidence; below 0.6 → treat as non-technical |
| `rationale` | string | Short debug explanation |

**Validation**: If `is_technical` is false, downstream research MUST NOT execute.

---

## New (ephemeral): ReferenceSnippet

| Field | Type | Description |
|---|---|---|
| `source` | enum | `official_docs`, `article`, `improvement_guide` |
| `title` | string | Page or doc section title |
| `url` | string | Source URL (may be empty for Context7 excerpts) |
| `excerpt` | string | Trimmed text injected into LLM prompt |
| `provider` | string | `context7`, `exa`, `opensearch` |

---

## New (ephemeral): ReferenceBundle

| Field | Type | Description |
|---|---|---|
| `topic` | string | Session topic |
| `snippets` | list[ReferenceSnippet] | Merged, de-duplicated excerpts |
| `providers_attempted` | list[string] | e.g. `["context7", "exa"]` |
| `providers_succeeded` | list[string] | Subset that returned snippets |
| `fetch_errors` | list[string] | Human-readable error summaries for logging |

**Lifecycle**: Created during `ContentAnalysisAgent.analyse()`, discarded after `ContentAnalysisPayload` is returned.

**Size limits**: Max ~14k chars total injected reference text (leaves room for 12k transcript cap).

---

## Report API projection

`GET /sessions/{id}/report` gains optional field:

| Field | Type | Description |
|---|---|---|
| `content_research_status` | string | Mirrors `research_status` from content analysis |

Insights array may include a synthetic content insight when status is `partial` or `skipped`:

- Type: `IMPROVEMENT`
- Message: `"Reference lookup unavailable — scores based on transcript analysis only."` (or partial variant)

---

## Frontend: ReportData extension

| Field | Type | Description |
|---|---|---|
| `content_research_status` | optional string | Drives disclaimer/status line in Technical Content panel |

---

## Configuration entities (environment)

| Variable | Required | Purpose |
|---|---|---|
| `EXA_API_KEY` | for live article search | Enables Exa provider |
| `CONTEXT7_API_KEY` | optional | Context7 rate limits |
| `CONTENT_RESEARCH_ENABLED` | no (default `true`) | Master switch |
| `CONTENT_RESEARCH_TIMEOUT_S` | no (default `20`) | Parallel fetch wall clock |
| `OPENSEARCH_URL` | no | Future optional article backend |

**Rule**: Missing keys for a provider → skip that provider, not fail analysis.

---

## Relationships

```text
Session (1) ──has──▶ topic, topic_context
Session (1) ──has──▶ TranscriptEntry[*]
Session (1) ──has──▶ SlideAnalysis[*] (optional enrichment)

ContentAnalysisAgent.analyse(session_id):
  Session + Transcript ──▶ TopicClassification
  TopicClassification (if technical) ──▶ ReferenceBundle
  Transcript + ReferenceBundle ──▶ ContentAnalysisPayload
  ContentAnalysisPayload ──▶ ReportAgent ──▶ Report (persisted)
```

---

## State transitions: research_status

```text
[transcript empty] ──▶ not_applicable (score 0)
[non-technical]    ──▶ not_applicable
[technical + all providers OK] ──▶ full
[technical + some providers OK] ──▶ partial
[technical + none OK / disabled] ──▶ skipped
```
