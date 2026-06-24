"""PPTXAgent — parses uploaded deck, evaluates against Tikal 12-factor Playbook.

Runs post-upload (background task). Per §10b.6 — slide raw text persisted to
sessions.slides_raw_text BEFORE LLM call so container restart survives.
"""

from __future__ import annotations

import asyncio
import uuid

from agno.agent import Agent
from loguru import logger
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from agents.llm import (
    call_with_fallback,
    get_text_model,
    get_text_model_fallback,
    pick_provider_order,
)
from agents.persistence import AgentPersistence
from agents.replay_fixtures import replay_slide_findings
from agents.schemas import SlideAnalysisPayload, SlideFindings
from config import get_settings
from db.repository import PostgreSQLRepository
from orchestrator.orchestrator import Orchestrator

PLAYBOOK_PROMPT = """You are a slide deck reviewer trained on the Tikal Presentation Skills Playbook.
Your job is to evaluate every slide in the deck and return specific, actionable findings.

## Rubric (Tikal Presentation Skills Playbook)
  1  Slides support the talk — they are NOT the talk. Plan the talk first as if there
     were no slides at all; only then think about slides.
  2  Authenticity — content should be original, unfamiliar, refreshing. If borrowing
     from specific sources, credit them on the slide.
  3  Keep it visual — limit text and bullet points; present information in small chunks.
     A picture is worth a thousand words; a funny/interesting picture is worth even more.
     Use high-resolution images.
  4  10-20-30 rule — ~10 slides, ~20 minutes, font size ≥ 30.
  5  Object count ≤6 per slide — the human brain counts up to 6 instantly; 7+ causes
     a delay. Avoid redundant slide numbers and logos on every slide.
  6  Dark background + bright text — high contrast keeps eyes on screen when needed;
     a blank slide lets the speaker reclaim all attention.
  7  Consistent fonts, headers, and title sizes across all slides.
  8  Story structure — slides should reflect a narrative arc: disruptive opening →
     hero encounters problem → naive solution fails → inspiration → solution → aftermath.
  9  Code display — animate or highlight specific lines; never dump a wall of unscoped
     code. Always have a Plan B (code pre-written in slides or a pre-recorded clip).
 10  Speaker notes belong in the notes area, NOT on the slide itself.
 11  Blank slides — insert one when you want all focus on the speaker.
 12  From subject to story — the deck should feel like a story, not an assorted
     collection of facts. The audience should always wonder "what happens next".

## What NOT to do
- Do not give generic advice like "add more images" without referencing the specific slide.
- Do not invent slide content — only evaluate what is explicitly shown to you.
- Do not emit more than 3 findings per slide — pick the most impactful ones.
- You receive extracted text plus structural metadata only — never the rendered slide.
  Do NOT comment on color, contrast, or background (Factor #6) — that data isn't provided.
- Only raise a font-size finding (Factor #4) when a slide's metadata line lists an explicit
  size below 30pt. If metadata says no explicit sizes were detected, say nothing about font size.
- Only say a slide "has visuals" or "uses an image" when its metadata line reports images > 0.
  Never infer an image's existence from the text content alone.
- Object-count findings (Factor #5) must match the "objects" count given in metadata, not a
  guess from the text.

## Output format
Return JSON only:
{"findings": [{
  "slide_index": int (1-based),
  "playbook_factor": int (1-12, must match the rubric above),
  "finding_type": "STRENGTH" | "IMPROVEMENT",
  "description": string (≤140 chars, slide-specific and actionable)
}]}

Cover at least 5 distinct factors across the deck. Both STRENGTH and IMPROVEMENT findings are welcome.

## Examples of good findings
{"slide_index": 2, "playbook_factor": 3, "finding_type": "IMPROVEMENT",
 "description": "Slide 2 has 9 bullet points. Cut to ≤3 key ideas and move the rest to speaker notes."}

{"slide_index": 5, "playbook_factor": 8, "finding_type": "STRENGTH",
 "description": "Slide 5 opens with a question that challenges assumptions — strong disruptive opening."}

{"slide_index": 8, "playbook_factor": 9, "finding_type": "IMPROVEMENT",
 "description": "Slide 8 shows a full 40-line code block. Highlight only the 3 relevant lines; move the rest off screen."}"""


class PPTXAgent(AgentPersistence):
    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator

    async def analyse(self, session_id: uuid.UUID, pptx_path: str) -> None:
        try:
            slides_raw = await asyncio.to_thread(self._extract_text, pptx_path)
        except Exception as exc:  # noqa: BLE001
            logger.exception("PPTX parse failed: {}", exc)
            slides_raw = []

        if get_settings().demo_replay:
            findings = replay_slide_findings()
        else:
            try:
                findings = await self._evaluate(slides_raw)
            except Exception as exc:  # noqa: BLE001
                logger.exception("PPTX LLM eval failed: {}", exc)
                findings = []

        # This agent owns slide_analyses + sessions(pptx) writes (Principle II).
        # Order preserved from the prior Orchestrator write: findings, then pptx_ready.
        async def write(repo: PostgreSQLRepository) -> None:
            await repo.insert_slide_analyses(
                [
                    {
                        "session_id": session_id,
                        "slide_index": f.slide_index,
                        "playbook_factor": f.playbook_factor,
                        "finding_type": f.finding_type,
                        "description": f.description,
                    }
                    for f in findings
                ]
            )
            await repo.mark_pptx_ready(session_id, slides_raw)

        await self._with_repo(write)
        await self.orchestrator.notify_complete(session_id, "PPTX")

    @staticmethod
    def _extract_text(path: str) -> list[dict]:
        deck = Presentation(path)
        out: list[dict] = []
        for idx, slide in enumerate(deck.slides, start=1):
            texts: list[str] = []
            font_sizes_pt: list[float] = []
            image_count = 0
            for shape in slide.shapes:
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    image_count += 1
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        line = "".join(run.text for run in para.runs).strip()
                        if line:
                            texts.append(line)
                        for run in para.runs:
                            if run.font.size is not None:
                                font_sizes_pt.append(run.font.size.pt)
            out.append(
                {
                    "slide_index": idx,
                    "text": "\n".join(texts),
                    "shape_count": len(slide.shapes),
                    "image_count": image_count,
                    "font_sizes_pt": font_sizes_pt,
                }
            )
        return out

    @staticmethod
    def _format_slide(row: dict) -> str:
        sizes = row.get("font_sizes_pt") or []
        size_note = f"{min(sizes):.0f}-{max(sizes):.0f}pt" if sizes else "none detected — do not judge font size"
        meta = f"objects: {row['shape_count']}, images: {row['image_count']}, explicit font sizes: {size_note}"
        return f"=== Slide {row['slide_index']} ({meta}) ===\n{row['text']}"

    async def _evaluate(self, slides_raw: list[dict]) -> list[SlideAnalysisPayload]:
        deck_dump = "\n\n".join(self._format_slide(row) for row in slides_raw)
        agent = Agent(
            model=get_text_model(),
            instructions=PLAYBOOK_PROMPT,
            output_schema=SlideFindings,
        )

        async def _gateway():
            return await agent.arun(deck_dump)

        fb = get_text_model_fallback()

        async def _claude():
            return await Agent(model=fb, instructions=PLAYBOOK_PROMPT, output_schema=SlideFindings).arun(deck_dump)

        claude_fn = _claude if fb else None
        primary, secondary = pick_provider_order(claude_fn, _gateway)
        result = await call_with_fallback(primary, secondary)
        logger.info("PPTX LLM result: {} findings", len(result.content.findings))
        return result.content.findings
