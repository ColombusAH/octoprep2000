# Contracts: Pre-Session Topic Research Persistence

**Version**: 1.0 | **Date**: 2026-06-24

This feature changes internal agent/workflow contracts and the `sessions` persistence shape. No public HTTP/WebSocket request or response shape changes (the existing `GET /sessions/{id}` already returns `pptx_ready`; the report API `content_research_status` field and values are unchanged).

---

## Contract A — `PPTXAgent.research` (internal, new)

**Module**: `agents/pptx_agent.py`

```python
async def research(
    self, topic: str, topic_context: str | None
) -> tuple[ReferenceBundle | None, ResearchStatus]:
    ...
```

**Behavior**:
- Under `DEMO_MODE=replay`: no live fetch; returns `(None, "not_applicable")`.
- Calls `classify_topic(topic, topic_context)`. Non-technical / confidence < 0.6 / empty topic → `(None, "not_applicable")`.
- Technical → `fetch_reference_bundle(topic, classification, include_improvements=True)`, then `compute_research_status(...)`. Returns `(bundle, status)`.
- MUST NOT raise on provider failure; `fetch_reference_bundle` already contains errors → status `partial`/`skipped`.

---

## Contract B — `PptxPrepWorkflow` step order (internal, changed)

**Module**: `workflows/pptx_prep.py`

Steps become: `extract → review → research → write`.

```python
async def research_step(_si: StepInput) -> StepOutput:
    ctx["bundle"], ctx["research_status"] = await agent.research(
        session.topic, session.topic_context
    )
    return StepOutput(content=f"research: {ctx['research_status']}")
```

- `research_step` MUST run before `write_step` (guarantees the `pptx_ready` gate covers research).
- `research_step` MUST be wrapped so an unexpected exception is logged and yields `(None, "skipped")` without aborting the workflow — `write_step` MUST still run (FR-007).
- The workflow stays pure glue: `telemetry=False, db=None`, no writes.

---

## Contract C — `PPTXAgent.persist` (internal, extended)

```python
async def persist(
    self,
    session_id: uuid.UUID,
    slides_raw: list[dict],
    findings: list[SlideAnalysisPayload],
    bundle: ReferenceBundle | None = None,
    research_status: ResearchStatus = "not_applicable",
) -> None:
    ...
```

- Writes slide_analyses (unchanged), then persists research + marks deck ready **in one commit ordering**: research columns then `pptx_ready` (so `pptx_ready=true` is never observed before research is saved).
- `notify_complete(session_id, "PPTX")` still fires after the commit (durability before notify, Principle II).

---

## Contract D — Repository (internal, extended)

**Module**: `db/repository.py`

```python
async def mark_pptx_ready(
    self,
    session_id: uuid.UUID,
    slides_raw: list[dict[str, Any]],
    research_bundle: dict | None = None,
    content_research_status: str | None = None,
) -> None:
    # sets pptx_ready=True, slides_raw_text, research_bundle, content_research_status
    ...
```

- Setting `research_bundle` / `content_research_status` is part of the same commit that flips `pptx_ready`.
- Reading is via the existing `get_session` (columns now present on the `Session` model) — no new read method strictly required; content agent reads `session.research_bundle` / `session.content_research_status`.

---

## Contract E — `ContentAnalysisAgent.analyse` (internal, changed)

**Module**: `agents/content_agent.py`

**Before**: classify topic → fetch bundle (live) → evaluate.
**After**: read `session.research_bundle` + `session.content_research_status` → reconstruct `ReferenceBundle` → evaluate.

- MUST NOT call `classify_topic` or `fetch_reference_bundle` (no live provider calls) — SC-001.
- `research_status` = persisted `session.content_research_status` (default `not_applicable` if null).
- If `research_bundle` is null/unparseable → `bundle=None`, transcript-only evaluation, status as persisted/`not_applicable` (FR-008).
- Output `ContentAnalysisPayload` shape unchanged.

**Invariant test**: with Context7/Exa clients patched to raise on any call, report generation for a session with a persisted bundle MUST succeed and make zero client calls.

---

## Contract F — `ReferenceBundle` (de)serialization (internal, new helpers)

**Module**: `agents/content_research/reference_bundle.py`

```python
def to_jsonb(bundle: ReferenceBundle) -> dict          # bundle.model_dump()
def from_jsonb(data: dict | None) -> ReferenceBundle | None  # ReferenceBundle(**data); None on falsy/invalid
```

- `from_jsonb(None)` → `None`. Invalid/legacy shape → `None` (logged), enabling the FR-008 fallback.

---

## Contract G — Frontend gate timeout (changed)

**Module**: `packages/web-dashboard/app/lib/api.ts`

- `waitForPptxReady` default `timeoutMs` raised from `45_000` to ≥ `60_000` to accommodate the added research phase (≤ `content_research_timeout_s`, default 20s) on top of extract+review. Polling field (`session.pptx_ready`) and interval unchanged.

---

## Migration

**File**: `migrations/versions/<rev>_add_session_research.py`

```python
revision = "<rev>"
down_revision = "a1b2c3d4e5f6"

def upgrade():
    op.add_column("sessions", sa.Column("research_bundle", postgresql.JSONB, nullable=True))
    op.add_column("sessions", sa.Column("content_research_status", sa.String(length=32), nullable=True))

def downgrade():
    op.drop_column("sessions", "content_research_status")
    op.drop_column("sessions", "research_bundle")
```
