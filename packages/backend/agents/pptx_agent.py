"""PPTXAgent — parses uploaded deck, evaluates against Tikal 12-factor Playbook.

Runs post-upload (background task). Per §10b.6 — slide raw text persisted to
sessions.slides_raw_text BEFORE LLM call so container restart survives.
"""

from __future__ import annotations

import asyncio
import json
from loguru import logger
import uuid

from pptx import Presentation

from agents.llm import get_llm
from agents.replay_fixtures import replay_slide_findings
from agents.schemas import SlideAnalysisBundle, SlideAnalysisPayload
from config import get_settings
from orchestrator.agno_orchestrator import AgnoOrchestrator


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


class PPTXAgent:
    def __init__(self, orchestrator: AgnoOrchestrator) -> None:
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

        await self.orchestrator.on_slide_analysis(
            SlideAnalysisBundle(
                session_id=session_id,
                findings=findings,
                slides_raw_text=slides_raw,
            )
        )

    @staticmethod
    def _extract_text(path: str) -> list[dict]:
        deck = Presentation(path)
        out: list[dict] = []
        for idx, slide in enumerate(deck.slides, start=1):
            texts: list[str] = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        line = "".join(run.text for run in para.runs).strip()
                        if line:
                            texts.append(line)
            out.append({"slide_index": idx, "text": "\n".join(texts)})
        return out

    async def _evaluate(self, slides_raw: list[dict]) -> list[SlideAnalysisPayload]:
        s = get_settings()
        client = get_llm()
        deck_dump = "\n\n".join(
            f"=== Slide {row['slide_index']} ===\n{row['text']}" for row in slides_raw
        )
        resp = await client.chat.completions.create(
            model=s.litellm_text_model,
            messages=[
                {"role": "system", "content": PLAYBOOK_PROMPT},
                {"role": "user", "content": deck_dump},
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )
        data = json.loads(resp.choices[0].message.content or '{"findings": []}')
        findings: list[SlideAnalysisPayload] = []
        for raw in data.get("findings", []):
            try:
                findings.append(SlideAnalysisPayload(**raw))
            except Exception as exc:  # noqa: BLE001
                logger.warning("invalid slide finding skipped: {} ({})", raw, exc)
        return findings
