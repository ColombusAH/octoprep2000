# Data Model: Pre-Session Topic Research Persistence

**Feature**: `002-pre-session-research` | **Date**: 2026-06-24

## Overview

One persistent change: the `sessions` table gains two nullable columns to hold the pre-session research output. The ephemeral `ReferenceBundle` / `ReferenceSnippet` / `TopicClassification` structures (from feature 001) are reused unchanged in memory; they are now serialized to JSONB at pre-session time and deserialized at report time. No new tables.

---

## Extended: `Session` (table `sessions`)

Existing columns unchanged. Added:

| Field | Type | Nullable | Description |
|---|---|---|---|
| `research_bundle` | JSONB | yes | Serialized `ReferenceBundle` gathered during pre-session prep. `null` until prep runs, or when research is `not_applicable`/`skipped` with no snippets. |
| `content_research_status` | String(32) | yes | `full` / `partial` / `skipped` / `not_applicable`. Set at pre-session time. `null` only before prep runs. |

**Writer**: `PPTXAgent` (same agent that already writes `pptx_ready` and `slides_raw_text`). One writer per role-scoped table preserved (Constitution II).

**Reader**: `ContentAnalysisAgent` (report time, read-only).

**Note**: `reports.content_research_status` (added in feature 001) stays as the report-facing field, populated by `ReportAgent` from the content payload. The new `sessions.content_research_status` is the pre-session source of truth.

---

## Persisted shape: `research_bundle` JSONB

Serialized from the existing `ReferenceBundle` Pydantic model (`agents/content_research/reference_bundle.py`) via `model_dump()`:

```json
{
  "topic": "string",
  "snippets": [
    {
      "source": "official_docs | article | improvement_guide",
      "title": "string",
      "url": "string",
      "excerpt": "string",
      "provider": "context7 | exa"
    }
  ],
  "providers_attempted": ["context7", "exa"],
  "providers_succeeded": ["context7"],
  "fetch_errors": ["exa: timed out after 20s"]
}
```

**Caps (unchanged)**: total excerpt text ≤ `MAX_TOTAL_CHARS` (14,000); per-snippet caps per `MAX_SNIPPET_CHARS`. Enforced at `add_snippet` time during the pre-session fetch, so the persisted JSONB is already bounded (FR-009 / SC-005).

**Round-trip**: a deserialize helper rebuilds `ReferenceBundle(**research_bundle)`; `blocks_by_source()` then feeds `_build_evaluation_prompt` exactly as today.

---

## Reused (ephemeral, unchanged): `TopicClassification`

Produced at the **start of pre-session research** (was: start of content analysis). Not persisted (only its effect — fetched snippets + status — is saved).

| Field | Type | Description |
|---|---|---|
| `is_technical` | bool | Gates whether providers run. |
| `primary_libraries` | list[str] (≤2) | Context7 library hints. |
| `confidence` | float 0–1 | <0.6 → treat as non-technical. |
| `rationale` | str | Debug. |

---

## State transitions: `content_research_status`

Computed at pre-session time by `compute_research_status` (unchanged logic), then persisted:

```text
[demo replay]                         ──▶ not_applicable (no live fetch)
[topic empty / missing]               ──▶ not_applicable (no fetch)
[non-technical or confidence < 0.6]   ──▶ not_applicable
[technical + all providers OK]        ──▶ full
[technical + some providers OK]       ──▶ partial
[technical + none OK / disabled / timeout] ──▶ skipped
```

At report time the status is **read**, not recomputed. If the session row has no status (prep never ran), the content agent defaults to `not_applicable` and runs transcript-only.

---

## Relationships

```text
Session (1) ──has──▶ topic, topic_context, slides_raw_text, pptx_ready
Session (1) ──has──▶ research_bundle (JSONB), content_research_status   [NEW]
Session (1) ──has──▶ TranscriptEntry[*]

Pre-session (PptxPrepWorkflow):
  Session.topic ──▶ TopicClassification ──(if technical)──▶ ReferenceBundle + status
  ReferenceBundle + status ──▶ persisted on Session row (in the mark_pptx_ready write)

Report time (ReportWorkflow → ContentAnalysisAgent):
  Session.research_bundle + status + Transcript ──▶ ContentAnalysisPayload
                                                     (NO provider calls)
  ContentAnalysisPayload ──▶ ReportAgent ──▶ reports.content_research_status (persisted)
```

---

## Validation rules

- `content_research_status` MUST be one of the four enum values when non-null.
- `research_bundle` MUST be `null` or a valid serialized `ReferenceBundle`; an unparseable value is treated as absent (FR-008 fallback) and logged.
- Persisting research MUST NOT block `mark_pptx_ready`: if research raised/timed out, status is `skipped` (or `partial`) and `research_bundle` holds whatever snippets succeeded (possibly `null`).
- Re-running pre-session prep for a session overwrites both columns (FR-012) — no accumulation.
