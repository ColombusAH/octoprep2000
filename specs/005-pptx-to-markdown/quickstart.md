# Quickstart & Validation Guide: PPTX-to-Markdown Pre-Processing

**Feature**: 005-pptx-to-markdown
**Date**: 2026-06-24

## Prerequisites

```bash
make install   # installs markitdown[pptx] via uv after pyproject.toml update
make db-up
```

Confirm the dependency is installed:
```bash
cd packages/backend && .venv/bin/python -c "from markitdown import MarkItDown; print('ok')"
```

---

## Scenario 1: MarkItDown text reaches the LLM prompt (unit)

**What to verify**: `_markitdown_texts` parses the `<!-- Slide number: N -->` separators and strips the `### Notes:` section.

**Run**:
```bash
cd packages/backend && .venv/bin/pytest tests/test_pptx_agent.py -k "markitdown" -v
```

**Expected**: New tests for `_markitdown_texts` pass; text contains Markdown headings (`#`), not raw concatenated lines.

---

## Scenario 2: `slides_raw` metadata unchanged (unit)

**What to verify**: `_extract_text` still populates `shape_count`, `image_count`, `font_sizes_pt`, `text_line_count`, `notes_text`, `notes_overlap_body`, `is_blank` correctly after the MarkItDown integration.

**Run**:
```bash
cd packages/backend && .venv/bin/pytest tests/test_pptx_agent.py::test_extract_text_metadata -v
cd packages/backend && .venv/bin/pytest tests/test_pptx_agent.py::test_extract_reat_example_deck -v
```

**Expected**: All existing assertions pass without modification.

---

## Scenario 3: Fallback on MarkItDown failure (unit)

**What to verify**: When `MarkItDown().convert()` raises, `_extract_text` falls back to python-pptx text and does not propagate the exception.

**Run**:
```bash
cd packages/backend && .venv/bin/pytest tests/test_pptx_agent.py -k "fallback" -v
```

**Expected**: Test mocks `MarkItDown.convert` to raise; `_extract_text` returns valid `slides_raw` with non-empty `text` fields from python-pptx.

---

## Scenario 4: Token count regression check (manual)

**What to verify**: The formatted deck dump for a real deck is shorter with MarkItDown text than with the previous format.

**Run**:
```bash
cd packages/backend && .venv/bin/python - <<'EOF'
from agents.pptx_agent import PPTXAgent
import pathlib, sys

deck = pathlib.Path("../../docs/testing/reat-19.2-news-example.pptx")
if not deck.exists():
    print("SKIP: test deck not found")
    sys.exit(0)

rows = PPTXAgent._extract_text(str(deck))
dump = PPTXAgent.build_deck_dump(rows)
print(f"Slides: {len(rows)}")
print(f"Dump length (chars): {len(dump)}")
# Spot-check: first slide text should contain a Markdown heading
print(f"Slide 1 text[:100]: {rows[0]['text'][:100]!r}")
EOF
```

**Expected**: Output includes `#` heading characters in slide text; dump length is visible for comparison against the pre-change baseline.

---

## Scenario 5: End-to-end demo path (integration)

**What to verify**: Full upload → analysis → report flow is unbroken.

**Run**:
```bash
make dev   # db + backend + frontend

# In a second terminal, upload a deck via the frontend at http://localhost:3000
# or via curl:
curl -X POST http://localhost:8000/sessions \
  -F "file=@docs/testing/reat-19.2-news-example.pptx" \
  -F "topic=Test Topic"

# Poll pptx_ready, then check the report endpoint
```

**Expected**: Session report renders slide findings at `/session/:id/report`; no 500 errors in backend logs.

---

## Scenario 6: DEMO_MODE replay unaffected

```bash
DEMO_MODE=replay make backend
# Upload any .pptx; report should render from fixtures without calling MarkItDown
```

**Expected**: Replay findings appear; no MarkItDown import errors.
