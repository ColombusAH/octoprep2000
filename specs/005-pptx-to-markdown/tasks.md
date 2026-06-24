# Tasks: PPTX-to-Markdown Pre-Processing

**Input**: Design documents from `specs/005-pptx-to-markdown/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

---

## Phase 1: Setup

- [x] T001 Add `"markitdown[pptx]>=0.1.6"` to `[project.dependencies]` in `packages/backend/pyproject.toml`, then run `make install`

---

## Phase 2: User Story 1 — Token-Efficient Deck Analysis (P1)

**Goal**: MarkItDown Markdown replaces raw python-pptx body text in the `text` field of `slides_raw`; all structural metadata unchanged.

**Independent Test**: Run `pytest tests/test_pptx_agent.py` — all existing tests pass; new tests for `_markitdown_texts` pass.

- [x] T002 [US1] Add static method `PPTXAgent._markitdown_texts(path: str) -> dict[int, str]` to `packages/backend/agents/pptx_agent.py` — splits MarkItDown output on `<!-- Slide number: N -->`, strips `### Notes:` section per slide, returns `{}` on any exception (see plan.md Step 2)
- [x] T003 [US1] Modify `PPTXAgent._extract_text` in `packages/backend/agents/pptx_agent.py` — call `_markitdown_texts` before the python-pptx loop; replace `"text": body_text` with `"text": md_texts.get(idx, body_text)`; keep `body_text` for `text_line_count`, `is_blank`, `notes_overlap_body` (see plan.md Step 3 and data-model.md)
- [x] T004 [US1] Add three tests to `packages/backend/tests/test_pptx_agent.py`: `test_markitdown_texts_parses_slides` (heading present, no `### Notes:`), `test_markitdown_texts_fallback_on_error` (mock raises → returns `{}`), `test_extract_text_uses_markitdown_text` (end-to-end: `text` has `#` heading, metadata fields still correct) — see plan.md Step 4

**Checkpoint**: `pytest tests/test_pptx_agent.py` fully green; `slides_raw[0]["text"]` contains a `#` Markdown heading for a test deck.

---

## Dependencies & Execution Order

- T001 → T002 → T003 → T004 (strictly sequential)

---

## Notes

- T002 and T003 are both in `pptx_agent.py`; do them sequentially to avoid conflicts.
- US2 (graceful degradation) is covered by `test_markitdown_texts_fallback_on_error` inside T004 — no separate phase needed.
- No DB migrations, no API contract changes, no WebSocket types to update.
