# Data Model: PPTX-to-Markdown Pre-Processing

**Feature**: 005-pptx-to-markdown
**Date**: 2026-06-24

## No schema changes

This feature makes no changes to any database table, SQLAlchemy model, Alembic migration, or WebSocket payload type.

The `sessions.slides_raw_text` column already stores a `list[dict]` as JSONB. Each dict's **`text`** field changes in content (from raw python-pptx body text to MarkItDown Markdown), but the field name, type (`str`), and column structure are unchanged.

---

## `slides_raw` dict — field-level delta

The `slides_raw` dict produced by `PPTXAgent._extract_text` is the only data structure affected.

| Field | Before | After | Source |
|---|---|---|---|
| `slide_index` | 1-based int | unchanged | python-pptx |
| `text` | raw body text joined by `\n` | MarkItDown Markdown (notes section stripped); falls back to raw body text on error | MarkItDown → fallback python-pptx |
| `shape_count` | int | unchanged | python-pptx |
| `image_count` | int | unchanged | python-pptx |
| `font_sizes_pt` | list[float] | unchanged | python-pptx |
| `text_line_count` | int | unchanged | python-pptx |
| `notes_text` | str (speaker notes) | unchanged | python-pptx |
| `notes_overlap_body` | bool | unchanged | python-pptx |
| `is_blank` | bool | unchanged | python-pptx |

**`is_blank` computation** — currently derived from `not body_text.strip() and image_count == 0`. After the change it must derive from the python-pptx body text (pre-MarkItDown substitution), not from the MarkItDown output. MarkItDown may emit an empty string for a blank slide but must not be the authoritative source for this flag.

---

## New internal helper

`PPTXAgent._markitdown_texts(path: str) -> dict[int, str]`

- Input: filesystem path to the uploaded PPTX
- Output: mapping of `{1-based slide index → stripped Markdown text}`
  - "Stripped" means the `### Notes:\n{...}` section is removed before storing
- Returns `{}` on any exception (triggers full fallback)
- Called once per deck, before the python-pptx shape loop

No persistent state. No DB read/write. No new repository method.

---

## `text_line_count` note

`text_line_count` currently counts non-empty lines from the python-pptx body text. This value is used by `validate_findings` and `_supplement_from_metadata` for Factor #3 (text density). It must continue to be derived from the python-pptx body text extraction, not from the MarkItDown `text` field, to ensure rubric thresholds remain consistent with the existing test baselines.
