# Quickstart & Validation: Pre-Session Topic Research Persistence

**Feature**: `002-pre-session-research` | **Date**: 2026-06-24

Validates that topic research runs and persists during pre-session prep, gates session start, and is reused at report time with zero live provider calls.

## Prerequisites

```bash
make db-up
make db-migrate          # applies the new sessions columns migration
cp .env.example .env     # ensure EXA_API_KEY / CONTEXT7_API_KEY set for live scenarios
make dev                 # backend :8000 + frontend :3000
```

For the resilience and "no live call" scenarios you can also run backend tests directly:

```bash
cd packages/backend && uv run pytest tests/test_pptx_agent.py tests/test_content_research.py -q
```

## Scenario 1 — Research persisted during pre-session prep (US1, FR-001/002/003)

1. Create a session with a technical topic (e.g. "React 19 new features").
2. Upload a `.pptx` (`POST /sessions/{id}/upload`).
3. Poll `GET /sessions/{id}` until `pptx_ready` is true.
4. Inspect the session row:
   ```sql
   SELECT content_research_status, jsonb_array_length(research_bundle->'snippets') AS snippets
   FROM sessions WHERE session_id = '<id>';
   ```

**Expected**: `content_research_status` is `full` or `partial`; `research_bundle` holds ≥1 snippet. This is saved *before* `pptx_ready` flipped true.

## Scenario 2 — Session start waits for research (US1 scenario 2, FR-006)

1. Upload a deck and immediately call `GET /sessions/{id}`.

**Expected**: `pptx_ready` is `false` until prep (extract → review → research → write) completes; the frontend Start button stays disabled until the poll sees `pptx_ready: true`. No separate timeline lets start unlock before research saves.

## Scenario 3 — Report reuses persisted research, zero live calls (US1 scenario 3, FR-004, SC-001)

1. With a session that has a persisted bundle, run a short rehearsal and end the session.
2. Generate/fetch the report (`GET /sessions/{id}/report`).

**Expected**: technical content findings reflect the persisted reference material; `content_research_status` matches the persisted session value. Backend logs show **no** Context7/Exa requests during report generation.

**Automated check**: in `tests/test_content_research.py`, patch `context7_client` and `exa_client` to raise on any call; assert content analysis for a session with a persisted bundle succeeds and the patched clients are never invoked.

## Scenario 4 — Research failure degrades, deck still ready (US2, FR-007, SC-004)

1. Set `EXA_API_KEY` / `CONTEXT7_API_KEY` to invalid values (or unset both).
2. Upload a deck for a technical topic.

**Expected**: prep still completes within the research timeout; `pptx_ready` becomes true; `content_research_status` is `skipped`; the later report still generates and surfaces the `skipped` insight.

## Scenario 5 — Non-technical topic skips research (US3, FR-005)

1. Create a session with a non-technical topic (e.g. "My summer vacation story").
2. Upload a deck, wait for `pptx_ready`.

**Expected**: `content_research_status` is `not_applicable`; `research_bundle` is null; no provider calls were made.

## Scenario 6 — Demo replay bypasses research (FR-009, SC-006)

1. Set `DEMO_MODE=replay`, restart backend.
2. Upload a deck, wait for `pptx_ready`, end session, view report.

**Expected**: no live research calls during prep; `content_research_status` is `not_applicable`; report renders from fixtures as today.

## Reference

- Data model: [data-model.md](./data-model.md)
- Contracts: [contracts/session-research.md](./contracts/session-research.md)
- Spec: [spec.md](./spec.md)
