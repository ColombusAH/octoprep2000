# Research: PPTX-to-Markdown Pre-Processing

**Feature**: 005-pptx-to-markdown
**Date**: 2026-06-24

## Decision 1: MarkItDown PPTX output format

**Decision**: Split the single Markdown string produced by `MarkItDown().convert(path)` using the `<!-- Slide number: N -->` HTML comment that MarkItDown inserts before each slide.

**Rationale**: Confirmed by live test against markitdown v0.1.6. Output for a 2-slide deck:
```
<!-- Slide number: 1 -->
# Hello World
Bullet A
Bullet B

### Notes:
Remember to speak slowly

<!-- Slide number: 2 -->
# Second Slide
```
Regex `r"<!-- Slide number: (\d+) -->"` extracts (slide_index, content) pairs reliably.

**Alternatives considered**:
- Parse MarkItDown's PPTX-specific internal API directly — not public; fragile across versions.
- Re-split by `# ` headings — unreliable when slide titles are absent or duplicated.

---

## Decision 2: Speaker notes handling

**Decision**: Strip the `### Notes:\n{text}` section from the MarkItDown text block before storing it in the `text` field of `slides_raw`. Continue using the python-pptx `_extract_notes` result for the `notes_text` field.

**Rationale**: The playbook rubric checks (Factor #10: notes-overlap-body) use `notes_text` from python-pptx. Including notes inline in `text` would double-count them in `build_deck_dump` and corrupt the `_notes_overlap_body` check.

**Alternatives considered**:
- Pass MarkItDown notes as `notes_text` — rejected; python-pptx notes are already extracted and the format is consistent; no benefit in switching source.

---

## Decision 3: python-pptx still runs for metadata

**Decision**: Retain the full python-pptx shape iteration loop in `_extract_text` for `shape_count`, `image_count`, `font_sizes_pt`, `text_line_count`, `notes_text`, `notes_overlap_body`, `is_blank`. Replace only the `text` field with the MarkItDown output.

**Rationale**: MarkItDown does not expose shape count, image count, font sizes, or speaker notes in a structured way. These fields drive deterministic supplement logic in `_supplement_from_metadata` and `validate_findings` (factors #3, #4, #5). Replacing them would require re-implementing equivalent python-pptx logic.

**Alternatives considered**:
- Remove python-pptx entirely and derive all metadata from the MarkItDown Markdown — rejected; MarkItDown does not expose shape count or font sizes.

---

## Decision 4: Fallback strategy

**Decision**: Wrap the MarkItDown conversion in a try/except at the deck level. If the full deck conversion raises, fall back to python-pptx body text for all slides and log a warning. If conversion succeeds but a particular slide's index is missing from the parsed output, fall back to python-pptx text for that slide only.

**Rationale**: Principle IV (Resilience Before Polish). A single corrupted slide or unsupported embedded object must not abort the analysis. The python-pptx body text is always available as a fallback because the metadata loop runs unconditionally.

**Alternatives considered**:
- Per-slide MarkItDown conversion (one call per slide) — rejected; MarkItDown accepts a file path, not a slide object. Splitting would require writing per-slide temp files, adding significant I/O overhead.

---

## Decision 5: MarkItDown instantiation

**Decision**: Construct `MarkItDown()` with no arguments (no `llm_client`, no `enable_plugins`) inside `_extract_text`. One instance per call; no global singleton.

**Rationale**: Text-only extraction is all that is required (FR-006). No LLM or OCR plugin is needed. Instantiation is cheap; a per-call instance avoids any thread-safety concerns in the async-to-thread context.

**Alternatives considered**:
- Module-level singleton — rejected; avoids exposing mutable global state in a test context and is premature optimization for an async-to-thread call that is not on the hot path.

---

## Decision 6: Where the MarkItDown call lives

**Decision**: Extract a private static method `_markitdown_texts(path: str) -> dict[int, str]` that returns `{1-based slide index → stripped markdown text}`. Call it from `_extract_text` before the python-pptx loop. If it raises, return an empty dict and log a warning; the loop then uses python-pptx body text for all slides.

**Rationale**: Isolates the MarkItDown dependency for testing. `_extract_text` is already a `@staticmethod` run in `asyncio.to_thread`; `_markitdown_texts` follows the same pattern.

---

## Decision 7: Dependency addition

**Decision**: Add `markitdown[pptx]>=0.1.6` to `[project.dependencies]` in `packages/backend/pyproject.toml`. No version pin beyond minimum.

**Rationale**: `markitdown[pptx]` pulls in `pptx` support via its own dependency; this does not conflict with `python-pptx>=0.6.23` which is already present (both use the same `python-pptx` package). The `[pptx]` extra ensures the PPTX converter is registered.

**Alternatives considered**:
- Separate `requirements.txt` entry — not used in this project; uv + pyproject.toml is the convention (Principle V).
