# Implementation Plan: PPTX-to-Markdown Pre-Processing

**Branch**: `005-pptx-to-markdown` | **Date**: 2026-06-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/005-pptx-to-markdown/spec.md`

## Summary

Replace the raw python-pptx body text in `PPTXAgent._extract_text` with MarkItDown-generated Markdown for the `text` field of each `slides_raw` dict. python-pptx continues to supply all structural metadata (shape counts, font sizes, image counts, speaker notes). The change is confined to one private method and one new private helper; no downstream interface, DB schema, API contract, or WebSocket type changes.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, agno, python-pptx>=0.6.23 (existing), markitdown[pptx]>=0.1.6 (new)
**Storage**: PostgreSQL 15 — `sessions.slides_raw_text` JSONB column; structure unchanged
**Testing**: pytest, pytest-asyncio; existing `tests/test_pptx_agent.py`
**Target Platform**: Linux server (Docker)
**Project Type**: Web service (backend only)
**Performance Goals**: Extract step completes within existing wall-clock budget for decks up to 30 slides
**Constraints**: Single FastAPI process; MarkItDown runs in `asyncio.to_thread` (same as existing extract); no LLM client
**Scale/Scope**: Per-session, one deck per upload

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Demo-First Vertical Slices | ✅ PASS | Core demo path (upload → analysis → report) preserved. `slides_raw` shape unchanged. |
| II. Contracted Agent Boundaries | ✅ PASS | PPTXAgent still owns the extract step and its DB writes. No ownership transfer. |
| III. Session Isolation | ✅ PASS | No auth, token, or session-scoping changes. |
| IV. Resilience Before Polish | ✅ PASS | Per-slide fallback to python-pptx on MarkItDown failure (FR-005). DEMO_MODE=replay unaffected. |
| V. Native Stack, Minimal Abstractions | ✅ PASS | `markitdown[pptx]` is a lightweight text extractor. No new service, queue, or storage layer. Justified by measurable token reduction; simpler alternative (manual XML parsing for Markdown) would be more complex. |

**Post-design re-check**: All principles still pass after Phase 1 design. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/005-pptx-to-markdown/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: decisions and rationale
├── data-model.md        # Phase 1: slides_raw field delta
├── quickstart.md        # Phase 1: validation scenarios
└── checklists/
    └── requirements.md
```

### Source Code (files affected)

```text
packages/backend/
├── pyproject.toml                     # Add markitdown[pptx]>=0.1.6
└── agents/
    └── pptx_agent.py                  # _markitdown_texts() + modified _extract_text()
        tests/
        └── test_pptx_agent.py         # New tests: _markitdown_texts, fallback
```

**Structure Decision**: Backend-only, single-project. Two files changed; no new modules.

## Triage Framework: [SYNC] vs [ASYNC] Classification

**Execution Strategy**: Mostly [SYNC] — changes are in a tightly coupled, well-tested core agent with existing baseline tests that must stay green.

### Preliminary Task Classification

| Task Category | Estimated [SYNC] Tasks | Estimated [ASYNC] Tasks | Rationale |
|---|---|---|---|
| Business Logic | 2 | 0 | `_markitdown_texts` + modified `_extract_text` require understanding of fallback contract |
| Testing | 1 | 0 | Must verify existing metadata tests still pass; new fallback test requires careful mocking |
| Infrastructure | 1 | 0 | Dependency addition is trivial but blocks everything |
| Data Operations | 0 | 0 | No DB changes |
| UI Components | 0 | 0 | Backend-only |

### Triage Audit Trail

| Task | Classification | Primary Criteria | Risk Level | Rationale |
|---|---|---|---|---|
| Add markitdown[pptx] dependency | SYNC | Touches pyproject.toml; unblocks all other tasks | Low | Mechanical but must be first |
| Implement `_markitdown_texts` | SYNC | New logic; fallback contract must match spec | Medium | Core new method; needs careful notes-stripping |
| Modify `_extract_text` to use MarkItDown text | SYNC | Modifies existing tested method; `is_blank` / `text_line_count` must keep python-pptx source | Medium | See data-model.md — `text_line_count` stays python-pptx |
| Add tests for `_markitdown_texts` and fallback | SYNC | Must cover success, notes stripping, and full-deck exception fallback | Low | Straightforward with mocking |

## Implementation Steps

### Step 1 — Dependency

**File**: `packages/backend/pyproject.toml`

Add `"markitdown[pptx]>=0.1.6"` to `[project.dependencies]`.

Run `make install` to regenerate the lockfile.

---

### Step 2 — New private method `_markitdown_texts`

**File**: `packages/backend/agents/pptx_agent.py`

Add a `@staticmethod` method to `PPTXAgent`:

```python
@staticmethod
def _markitdown_texts(path: str) -> dict[int, str]:
    """Convert PPTX to Markdown via MarkItDown; return {slide_index: md_text}.

    Strips the '### Notes:' section from each slide block to avoid duplicating
    speaker notes that are already captured via python-pptx. Returns {} on any
    error so the caller falls back to python-pptx body text.
    """
    import re
    from markitdown import MarkItDown

    try:
        result = MarkItDown().convert(path)
    except Exception:
        logger.warning("MarkItDown conversion failed for {}; falling back to python-pptx text", path)
        return {}

    raw = result.text_content or ""
    # Split on slide-number HTML comment markers
    parts = re.split(r"<!-- Slide number: (\d+) -->", raw)
    # parts layout: ['', '1', '<slide 1 content>', '2', '<slide 2 content>', ...]
    out: dict[int, str] = {}
    for i in range(1, len(parts) - 1, 2):
        idx = int(parts[i])
        body = parts[i + 1]
        # Strip the Notes section (### Notes:\n...) — it is captured separately
        body = re.sub(r"\n### Notes:\n.*", "", body, flags=re.DOTALL)
        out[idx] = body.strip()
    return out
```

---

### Step 3 — Modify `_extract_text`

**File**: `packages/backend/agents/pptx_agent.py`

At the top of `_extract_text(path)`:
1. Call `PPTXAgent._markitdown_texts(path)` to get `md_texts: dict[int, str]`.
2. In the slide loop, retain the full python-pptx body-text assembly (for `text_line_count`, `is_blank`, `notes_overlap_body`).
3. Replace the final `"text": body_text` with `"text": md_texts.get(idx, body_text)`.

The `idx` variable is the 1-based slide index already in scope as the loop variable.

Concrete diff (schematic):

```python
# BEFORE (inside _extract_text, end of loop body)
out.append({
    "slide_index": idx,
    "text": body_text,           # <-- was python-pptx body text
    ...
})

# AFTER
out.append({
    "slide_index": idx,
    "text": md_texts.get(idx, body_text),   # MarkItDown; fallback to python-pptx
    ...
})
```

The `md_texts` dict is populated once before the loop. `body_text` remains computed by the existing python-pptx loop for fallback and for `text_line_count` / `is_blank` / `notes_overlap_body`.

---

### Step 4 — Tests

**File**: `packages/backend/tests/test_pptx_agent.py`

Add three new test functions:

1. **`test_markitdown_texts_parses_slides`**: Build a 2-slide deck in a temp dir. Assert `_markitdown_texts` returns a dict with keys 1 and 2; slide 1 text contains `#` (Markdown heading); slide 1 text does NOT contain `### Notes:`.

2. **`test_markitdown_texts_fallback_on_error`**: Patch `markitdown.MarkItDown.convert` to raise `RuntimeError`. Assert `_markitdown_texts` returns `{}` without raising.

3. **`test_extract_text_uses_markitdown_text`**: Build a 2-slide deck. Assert `rows[0]["text"]` starts with `#` (Markdown heading from MarkItDown). Assert `rows[0]["text_line_count"]`, `rows[0]["notes_text"]`, `rows[0]["is_blank"]` are still correctly populated from python-pptx.

Existing tests (`test_extract_text_metadata`, `test_extract_reat_example_deck`, `test_format_slide_includes_notes_and_text_lines`) must continue to pass without modification.

---

## Complexity Tracking

No constitution violations. No complexity justification required.
