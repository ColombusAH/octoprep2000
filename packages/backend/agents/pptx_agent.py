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


PLAYBOOK_PROMPT = """You evaluate a slide deck against the Tikal Presentation Skills Playbook.

The 12 factors (verbatim from the Tikal handbook):
  1  Triangle of Alliances — slides support the talk, NOT replace it. Plan the talk first
     as if there were no slides at all; only then think about slides.
  2  Trust & Credibility — clarity of authorship, credentials shown when appropriate;
     a strong first impression (clean title slide) builds trust.
  3  Authenticity — content should be original, unfamiliar, refreshing. If borrowing
     from specific sources, credit them on the slide.
  4  Keep it visual — limit text and bullet points; present information in small chunks.
     A picture is worth a thousand words; an interesting picture is worth even more.
  5  10-20-30 rule — ~10 slides, ~20 minutes, font size ≥ 30.
  6  Use imagery — high-resolution images that support the message; avoid stock-photo cliché.
  7  Object count ≤6 per slide — the human brain counts up to 6 instantly; 7+ causes delay.
     Avoid redundant slide numbers and logos on every slide.
  8  Dark background + bright text — high contrast keeps eyes on screen; switching to a
     blank slide lets the speaker reclaim attention.
  9  Consistent fonts, headers, and title sizes across all slides.
 10  Code display — animate or highlight specific lines; never dump unscoped code.
     Have a Plan B for live coding (code on slides or pre-recorded clip).
 11  Speaker notes belong in the notes area, NOT on the slide itself.
 12  Blank slides — insert a blank when you want all attention on the speaker.

Return JSON only:
{"findings": [{
  "slide_index": int (1-based, matches the deck order shown to you),
  "playbook_factor": int (1-12, must match the factor numbering above),
  "finding_type": "STRENGTH" | "IMPROVEMENT",
  "description": "short, actionable, slide-specific (≤140 chars). Reference what is on
                  that slide. For STRENGTH: explain why it works. For IMPROVEMENT:
                  state the fix."
}]}

Cover at least 5 distinct factors across the deck. Prefer concrete, slide-anchored
findings over vague advice. Both Strengths and Improvements per deck are welcome."""


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
