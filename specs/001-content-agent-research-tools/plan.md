# Implementation Plan: Content Agent Research Tools

**Branch**: `content-agent` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-content-agent-research-tools/spec.md`

## Summary

Augment `ContentAnalysisAgent` with a bounded **research pre-fetch pipeline** for technical session topics. Before the existing structured LLM evaluation, the agent classifies the topic, fetches official documentation (Context7), articles and improvement guidance (Exa), assembles an ephemeral `ReferenceBundle`, and injects excerpts into the evaluation prompt. Non-technical topics and demo replay mode skip research. Failures degrade to transcript-only analysis with explicit `research_status` surfaced in the report API and Technical Content UI.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript (report UI touch-up)

**Primary Dependencies**: FastAPI, Agno, httpx (existing), **exa-py** (new), Tikal LiteLLM + optional Anthropic fallback (existing)

**Storage**: PostgreSQL unchanged — research data is ephemeral; only `research_status` flows through report JSON

**Testing**: pytest + pytest-asyncio; httpx mocks for Context7; stub Exa client

**Target Platform**: Single FastAPI process (local + Railway)

**Performance Goals**: 95% of report generations ≤60s with healthy providers; research phase ≤20s wall clock

**Constraints**: Constitution IV resilience; demo replay must bypass all research; no new DB tables for MVP

**Scale/Scope**: Post-session only, 1 analysis per session end, 2–4 external calls max per technical session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Gate | Status | Notes |
|---|---|---|
| **Demo path** | ✅ PASS | Replay mode bypasses research; upload → rehearse → end → report unchanged |
| **Agent contracts** | ✅ PASS | `ContentAnalysisPayload` extended with optional `research_status`; Orchestrator write path unchanged (`on_report` only) |
| **Session isolation** | ✅ PASS | Research reads only current session's topic/transcript/slides |
| **Resilience** | ✅ PASS | Per-provider timeouts, partial fallback, `DEMO_MODE=replay` preserved |
| **Stack simplicity** | ⚠️ JUSTIFIED | One new dependency (`exa-py`); Context7 via httpx (no MCP). See Complexity Tracking |
| **Validation** | ✅ PASS | Unit tests for research module + report status insight; quickstart manual scenarios |

**Post-design re-check**: All gates pass. No constitution amendment required.

## Project Structure

### Documentation (this feature)

```text
specs/001-content-agent-research-tools/
├── plan.md              # This file
├── research.md          # Phase 0 decisions
├── data-model.md        # Phase 1 entities
├── quickstart.md        # Validation guide
├── contracts/
│   └── content-research.md
└── tasks.md             # Phase 2 (/spec-tasks — not yet created)
```

### Source Code (repository root)

```text
packages/backend/
├── agents/
│   ├── content_agent.py              # Orchestrate classify → research → evaluate
│   ├── content_research/             # NEW package
│   │   ├── __init__.py
│   │   ├── classifier.py             # TopicClassification
│   │   ├── context7_client.py        # Official docs fetch
│   │   ├── exa_client.py             # Articles + improvement search
│   │   ├── reference_bundle.py       # Ephemeral merge + caps
│   │   └── errors.py                 # ResearchProviderError
│   ├── schemas.py                    # + research_status on payload
│   └── report_agent.py               # Status insight + API field
├── config.py                         # EXA_API_KEY, CONTEXT7_API_KEY, timeouts
├── routers/sessions.py               # Pass content_research_status in report JSON
└── tests/
    └── test_content_research.py      # NEW

packages/web-dashboard/
└── app/components/ScoreCard.tsx      # Disclaimer + research status text

packages/shared-types/
└── src/index.ts                      # Optional content_research_status on report type
```

**Structure Decision**: Monorepo layout unchanged. New code isolated under `agents/content_research/` to keep `content_agent.py` thin and testable.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| New dependency `exa-py` | Async article/improvement search with highlights | Raw REST duplicates SDK maintenance; spec names Exa as preferred provider |
| Context7 HTTP client | Live official docs for library topics | LLM-only evaluation misses version-specific facts; MCP subprocess adds ops burden |
| Topic classifier LLM call | Borderline technical topics | Keyword-only misclassifies mixed business/tech talks |

## Implementation Phases

### Phase A — Foundation (P1 resilience + classification)

1. Add config settings and `.env.example` entries.
2. Implement `TopicClassification` + `classifier.py`.
3. Implement `ReferenceBundle` + `errors.py`.
4. Extend `ContentAnalysisPayload` and `ContentResult` prompt to accept reference block.
5. Wire classifier into `content_agent.py` (non-technical path = current behavior).

### Phase B — Research providers (P1 accuracy)

1. Implement `context7_client.py` (resolve + query-docs via httpx).
2. Implement `exa_client.py` (coverage + improvement parallel searches).
3. Implement parallel fetch orchestration with `asyncio.wait_for` per provider.
4. Set `research_status` based on provider outcomes.

### Phase C — Report + UI (P1 visibility, P2 improvement copy)

1. `ReportAgent._content_breakdown`: prepend status insight when partial/skipped.
2. `sessions.py` report response: add `content_research_status`.
3. `ScoreCard.tsx`: conditional disclaimer + status text (accessibility: text, not color-only).
4. Update `shared-types` if report type is shared.

### Phase D — Tests + fixtures

1. `test_content_research.py`: classifier, bundle caps, degradation, replay bypass.
2. Extend replay fixture optionally with `research_status: not_applicable`.
3. Run quickstart scenarios.

## Prompt changes (evaluation LLM)

Replace single-shot transcript prompt with:

```text
Topic: {topic}
Research status: {research_status}

## Official documentation excerpts
{docs_block}

## Articles and expert sources
{articles_block}

## Improvement guidance
{improvement_block}

## Transcript
{transcript}

Evaluate accuracy and coverage against the topic using the reference material above.
Prefer official documentation over articles for factual disputes.
Produce improvement findings grounded in the improvement guidance section.
```

## Risk mitigations

| Risk | Mitigation |
|---|---|
| 60s report timeout | 20s research wall clock; truncate excerpts; skip slow providers |
| API cost on demo day | `DEMO_MODE=replay`; `CONTENT_RESEARCH_ENABLED=false` env kill switch |
| Context7 library mismatch | Classifier returns max 2 libraries; skip if resolve fails |
| Stale Exa results | Use `max_age_hours` or recent-focused queries |

## Validation plan

- **Automated**: `pytest tests/test_content_research.py`; existing `test_report_dedup.py` still passes
- **Manual**: `quickstart.md` scenarios 1–5
- **Demo**: Verify `DEMO_MODE=replay` on Fuse Day path before enabling live keys

## Artifacts generated

| Artifact | Path |
|---|---|
| Research decisions | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Contracts | [contracts/content-research.md](./contracts/content-research.md) |
| Quickstart | [quickstart.md](./quickstart.md) |
