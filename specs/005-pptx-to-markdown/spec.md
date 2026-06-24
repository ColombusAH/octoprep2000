# Feature Specification: PPTX-to-Markdown Pre-Processing

**Feature Branch**: `005-pptx-to-markdown`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "since a pptx make more tokens, convert that to md with https://github.com/microsoft/markitdown before we send it to the agents, use also context7 to learn"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Token-Efficient Deck Analysis (Priority: P1)

A developer or agent pipeline processes an uploaded PPTX deck before any LLM evaluation. Instead of building a verbose custom-formatted dump, the system produces a compact Markdown representation of the deck's text content via MarkItDown, combines it with the structural metadata already extracted (shape counts, font sizes, image counts), and sends the combined representation to the playbook-evaluation agent.

**Why this priority**: Every PPTX analysis call (static pass, delivery pass) sends the full deck dump to the LLM. Reducing that payload size directly lowers token cost and latency on every session.

**Independent Test**: Upload a PPTX deck and trigger the static analysis. Verify the prompt sent to the LLM contains MarkItDown-generated Markdown headings/bullets rather than the old `=== Slide N ===` custom format, while still embedding the metadata line (objects, images, text_lines, font sizes, speaker notes) required by the playbook rubric.

**Acceptance Scenarios**:

1. **Given** a PPTX file is uploaded and `PptxPrepWorkflow` runs, **When** the extract step completes, **Then** each `slides_raw` dict contains both the MarkItDown-generated text field and the python-pptx structural metadata (shape_count, image_count, font_sizes_pt, text_line_count, notes_text, is_blank, notes_overlap_body).
2. **Given** a `slides_raw` list with MarkItDown-generated text, **When** `build_deck_dump` formats the prompt, **Then** the formatted output is measurably shorter in character count than the prior format for the same deck, while retaining all metadata annotation lines.
3. **Given** `DEMO_MODE=replay`, **When** the extract step runs, **Then** it still returns valid `slides_raw` (replay fixtures are unaffected).

---

### User Story 2 - Graceful Degradation on Conversion Failure (Priority: P2)

If MarkItDown fails to convert a slide's content (corrupt shape, unsupported embedded object), the system falls back to the existing python-pptx text extraction for that slide rather than aborting the workflow.

**Why this priority**: Demo-day resilience. A single broken slide must not silence the entire playbook analysis.

**Independent Test**: Submit a PPTX with one slide containing an unsupported embedded object. Confirm the remaining slides are processed normally and at least one finding is returned in the report.

**Acceptance Scenarios**:

1. **Given** MarkItDown raises an exception for a single slide, **When** the extract step runs, **Then** that slide's text field is populated from the python-pptx fallback and a warning is logged.
2. **Given** MarkItDown raises an exception for all slides, **When** the extract step runs, **Then** all slides fall back to python-pptx extraction and the workflow continues normally.

---

### Edge Cases

- What happens when a PPTX has no text on any slide (all-image deck)? MarkItDown produces empty or near-empty Markdown; the existing `is_blank` metadata flag still fires correctly.
- What happens when speaker notes contain very long text? MarkItDown may include notes inline; the system must strip or truncate notes from the MarkItDown output and continue using the python-pptx-extracted notes field to avoid duplication.
- What happens when MarkItDown produces more tokens than the old format for a given deck? The feature ships the conversion regardless; the net token reduction is expected to be positive across typical decks. No automatic rollback is required.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST add `markitdown[pptx]` as a backend dependency and install it alongside the existing `python-pptx` dependency.
- **FR-002**: The extract phase of `PptxPrepWorkflow` MUST invoke MarkItDown on the PPTX file to produce a per-slide Markdown text representation before forwarding to the review phase.
- **FR-003**: The extract phase MUST continue using python-pptx to collect structural metadata (shape_count, image_count, font_sizes_pt, text_line_count, notes_text, notes_overlap_body, is_blank) for every slide, because this metadata drives deterministic rubric supplement logic that MarkItDown does not provide.
- **FR-004**: `build_deck_dump` MUST format the LLM prompt using the MarkItDown-generated text as the slide content block, with the structural metadata annotation line preserved in the same position as today.
- **FR-005**: If MarkItDown conversion fails for any slide, the system MUST fall back to the python-pptx text for that slide and log a warning; the workflow MUST NOT abort.
- **FR-006**: The MarkItDown conversion MUST run without an LLM client (text-only extraction, no image OCR) to avoid additional API calls during the extract phase.
- **FR-007**: The converted Markdown text MUST be stored in the `slides_raw` dict under a `text` key (replacing the current python-pptx body text), so all downstream consumers (`build_deck_dump`, `build_delivery_dump`, `validate_findings`) work without interface changes.

### Constitution-Aligned Requirements *(mandatory)*

- **CAR-001**: This feature affects the core demo path (PPTX upload → `PptxPrepWorkflow` → static analysis → report). It changes the content of the deck dump sent to the playbook agent but does not alter the route, WebSocket, or report surface.
- **CAR-002**: No API, WebSocket, agent payload, shared type, scoring weight, or database schema changes. The `slides_raw_text` column in the `sessions` table already stores the list of dicts; the `text` field within each dict changes in content but not in structure.
- **CAR-003**: No session-isolation or token-handling changes. The feature is entirely within the server-side extract step of `PptxPrepWorkflow`.
- **CAR-004**: Fallback required: if MarkItDown fails for a slide, the system uses the python-pptx text for that slide (FR-005). The existing `DEMO_MODE=replay` path is unaffected because it bypasses `_extract_text` entirely.
- **CAR-005**: No UI changes. Feature is backend-only.

### Key Entities

- **slides_raw (list[dict])**: Per-slide data bag produced by `PPTXAgent._extract_text` and consumed by `build_deck_dump`, `validate_findings`, and `_supplement_from_metadata`. The `text` field within each dict transitions from python-pptx body text to MarkItDown Markdown; all other fields remain unchanged.
- **MarkItDown converter instance**: A single `MarkItDown()` instance (no LLM client) constructed once per extract call and reused across all slides of a deck.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The character count of the formatted deck dump sent to the LLM decreases by at least 10% on average for a representative sample of typical presentation decks (5–15 slides, mixed text and bullet content).
- **SC-002**: The PPTX analysis pipeline produces the same number of slide findings (within ±1) for an identical deck before and after the change, confirming content fidelity is preserved.
- **SC-003**: The extract step completes within the same wall-clock budget as the prior python-pptx-only extraction for decks up to 30 slides (no measurable regression in workflow duration).
- **SC-004**: Zero unhandled exceptions from the extract step on a corpus of at least 5 diverse PPTX decks, including one with embedded images and one with no body text.

## Assumptions

- MarkItDown's PPTX output preserves slide heading hierarchy and bullet structure in Markdown form, which is sufficient for the playbook rubric's text-density and narrative-flow checks.
- MarkItDown does not natively produce per-slide shape counts, image counts, or explicit font sizes; python-pptx remains the authoritative source for those metadata fields.
- No LLM or image-description capability is needed during extraction (FR-006); MarkItDown is invoked in text-only mode.
- The `markitdown[pptx]` extra is compatible with the existing Python 3.11+ / uv environment and does not conflict with `python-pptx`.
- MarkItDown may include speaker notes inline in its Markdown output; the implementation will suppress or de-duplicate the notes section from the MarkItDown text to avoid confusing the rubric check for Factor #10 (notes-on-slide detection).
