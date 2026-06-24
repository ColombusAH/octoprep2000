# Contract: Agent-Owned Persistence

**Feature**: 001-agent-direct-persistence

Internal contract (single-process app). Defines what each agent MUST write and how, replacing the
Orchestrator-owned writes.

## Shared write helper

All agents persist through one helper that mirrors the Orchestrator's proven pattern:

```python
# fresh AsyncSession per write — no captured handle (B2 fix)
async def _with_repo(fn):
    async with get_session_maker()() as db:
        return await fn(PostgreSQLRepository(db))
```

Provided as an `AgentPersistence` mixin/util importable by every agent. Repository methods are
**unchanged**; only the caller moves from Orchestrator to agent.

## Per-agent obligations

### VisionAgent
- MUST buffer `VideoEventPayload`s and flush via `repo.bulk_insert_video_events(...)` at **N=20 or
  every 1s** (batching preserved, FR-009).
- MUST publish each event to `broadcaster` for live feedback (shape `FeedbackEvent`, unchanged).
- MUST `notify_complete(session_id, "VIDEO", {"events_flushed": n})` after each durable flush.
- On `end_session`, MUST flush remaining buffered events before returning (durability before report).
- MUST NOT write any table other than `video_events`.

### AudioAgent
- MUST write each transcript chunk via `repo.insert_transcript_entry(...)`.
- MUST write each warning via `repo.insert_audio_warning(...)` and publish it to `broadcaster`.
- MUST `notify_complete(session_id, "AUDIO")` per processed chunk (or per batch).
- MUST NOT write any table other than `transcript_entries` / `audio_warnings`.

### PPTXAgent
- MUST persist raw slide text **before** the LLM call (crash-survival, §10b.6) via
  `repo.mark_pptx_ready(session_id, slides_raw_text)` — preserving the existing ordering guarantee.
- MUST write findings via `repo.insert_slide_analyses(...)`.
- MUST `notify_complete(session_id, "PPTX")` after both writes commit.
- MUST NOT write any table other than `slide_analyses` / `sessions` (pptx fields only).

### ReportAgent
- MUST read all source tables (unchanged) AND now MUST write the report via
  `repo.insert_report(...)` itself, then `notify_complete(session_id, "REPORT")`.

### ContentAnalysisAgent
- Read-only (unchanged). MAY `notify_complete(session_id, "CONTENT")` when its analysis is consumed.

## Orchestrator obligations (after change)

- MUST NOT perform writes for `video_events`, `transcript_entries`, `audio_warnings`,
  `slide_analyses`, `reports`. (`on_video_event`/`on_transcript`/`on_audio_warning`/
  `on_slide_analysis`/`on_report` write bodies are removed.)
- MUST retain: `start_session`, `end_session`, `set_session_status` transitions,
  `activate_fallback`/`is_fallback`, and `REPORT_READY` / `FALLBACK_ACTIVATED` broadcasts.
- MUST assemble the report by reading the agreed tables (already true via ReportAgent).
- MUST expose `notify_complete(...)` and track per-session completion (`_completion`).

## Invariants

- **One writer per table** — no two agents write the same table; eliminates write races (Edge Cases).
- **Durability before notify** — an agent emits a completion signal only after its write commits.
- **Session scope** — every write/notify is scoped to an authenticated `session_id`; ingress auth
  (`validate_ws_token`, `require_session_owner`) is unchanged (CAR-003).
- **Outbound feedback shape unchanged** — `FeedbackEvent` and the realtime-feedback WS are stable
  (FR-008); `DEMO_MODE=replay` paths persist via the same agent helpers.
