# Research: Content Agent Research Tools

**Feature**: `001-content-agent-research-tools`  
**Date**: 2026-06-24

## R1: Research orchestration pattern

**Decision**: Use a **deterministic pre-fetch pipeline** followed by a single structured LLM evaluation call—not an open-ended agentic tool loop.

**Rationale**:
- Report generation has a hard 60s budget (constitution + PRD). Pre-fetch with `asyncio.gather` and per-provider timeouts makes latency predictable.
- Current `ContentAnalysisAgent` already uses one Agno `Agent.arun()` with `output_schema=ContentResult`. Injecting a `ReferenceBundle` into the prompt preserves that contract and minimizes refactor risk.
- Failures can be isolated per provider (docs vs articles vs improvement) and degraded independently.

**Alternatives considered**:
| Alternative | Rejected because |
|---|---|
| Agno agent with live tool calls in a loop | Unbounded turns risk exceeding 60s; harder to test and replay |
| Single mega-prompt with web search baked into LiteLLM | No control over provider choice; couples billing and failure modes |
| Persist reference bundles in PostgreSQL | Out of MVP scope per spec; adds migration and retention concerns |

---

## R2: Technical topic classification

**Decision**: Lightweight **LLM classification** using the existing text model with a tiny structured output (`is_technical: bool`, `primary_libraries: list[str]`, `confidence: float`). Fall back to keyword heuristics if the classifier call fails.

**Rationale**:
- Borderline topics ("AI trends for business leaders") need semantic judgment; keyword lists are brittle.
- `primary_libraries` seeds Context7 `resolve-library-id` without a second guessing step.
- One short LLM call (~1–2s) is acceptable inside the 60s envelope.

**Alternatives considered**:
| Alternative | Rejected because |
|---|---|
| User toggle "technical / non-technical" | Adds UX friction; spec assumes auto-classification |
| Always run research for every topic | Wastes API quota on narrative talks; violates FR-011 |
| Regex-only classifier | Too many false negatives on mixed business+tech topics |

---

## R3: Article and improvement search (Exa)

**Decision**: Integrate **Exa** via `exa-py` (`AsyncExa`) as the primary article search provider. Run **two parallel searches** for technical topics:

1. **Coverage / accuracy**: `"{topic}" official features documentation overview`
2. **Improvement**: `"{topic}" best practices common mistakes what to cover technical talk`

Use `contents={"highlights": True}`, `num_results=5` per query, cap total injected text at ~4k chars per query bucket.

**Rationale**:
- Exa is purpose-built for AI retrieval with async support matching FastAPI agents.
- Separate queries keep improvement guidance distinct from factual reference (FR-002 vs FR-003).
- Highlights reduce token load vs full page text.

**Alternatives considered**:
| Alternative | Rejected because |
|---|---|
| Raw httpx to Exa REST | Official SDK maintained; same dependency cost |
| OpenSearch as required path | No OpenSearch cluster in repo; spec treats it as optional future index |
| Single combined Exa query | Muddies improvement vs factual signals |

**OpenSearch (optional later)**: If `OPENSEARCH_URL` is configured, route article queries through OpenSearch instead of Exa for internal/demo corpora. Not required for MVP slice.

---

## R4: Official documentation (Context7)

**Decision**: Integrate **Context7 REST API** via `httpx` (already a project dependency)—no MCP subprocess in the backend.

Flow:
1. For each `primary_library` from classification (max 2), call resolve-library-id equivalent (`GET /api/v1/search?query=...` or documented search endpoint).
2. Call query-docs equivalent with library ID and queries:
   - `"{topic}" key features and API overview`
   - `"{topic}" breaking changes and version notes` (when version detectable in topic string)

Cap injected doc excerpts at ~6k chars total.

**Rationale**:
- Context7 MCP is designed for IDE agents; a FastAPI worker should use the HTTP API directly (simpler ops, no MCP child process).
- Official docs take precedence over articles for factual disputes (spec edge case).
- httpx avoids adding MCP client infrastructure.

**Alternatives considered**:
| Alternative | Rejected because |
|---|---|
| Context7 MCP server subprocess | Process management overhead; harder to timeout |
| Scrape docs manually | Fragile; defeats purpose of Context7 |
| Skip docs, Exa only | Misses authoritative API references for library-specific talks |

**Env**: `CONTEXT7_API_KEY` (optional; higher rate limits when set).

---

## R5: Time budget and resilience

**Decision**: Allocate sub-budgets inside the 60s report window:

| Phase | Budget |
|---|---|
| Topic classification | 5s |
| Parallel research (Exa ×2 + Context7 ×1–2) | 20s total (per-call timeout 15s) |
| Content LLM evaluation | 25s |
| Report aggregation (unchanged) | remainder |

On any failure: use partial `ReferenceBundle`, set `research_status` to `partial` or `skipped`, never return `None` from content agent solely due to research failure.

**Rationale**: Constitution principle IV; FR-008/FR-009. ReportAgent already handles `content is None` poorly (score 0 + "skipped")—research failures must not collapse to that path.

---

## R6: Contract and UI surfacing

**Decision**: Extend `ContentAnalysisPayload` with optional `research_status: "full" | "partial" | "skipped" | "not_applicable"`. Pass through report API JSON. Frontend shows status text under Technical Content panel; update disclaimer copy.

**Rationale**: FR-012, SC-006, CAR-005. Backward-compatible optional field; `ReportAgent._content_breakdown` prepends a status insight when not `full`.

**Alternatives considered**:
| Alternative | Rejected because |
|---|---|
| New DB table for research artifacts | Over-engineering for ephemeral data |
| Hide status in logs only | Fails user-facing success criteria |

---

## R7: Testing strategy

**Decision**:
- Unit tests with `httpx.MockTransport` for Context7 + mocked Exa client.
- Integration test: technical topic fixture transcript → assert `research_status` and finding types.
- Replay mode test unchanged.
- Manual quickstart scenarios in `quickstart.md`.

**Rationale**: Constitution validation gates require automated tests for agent/scoring changes.
