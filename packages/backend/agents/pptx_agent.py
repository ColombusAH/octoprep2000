"""PPTXAgent — parses uploaded deck, evaluates against Tikal 12-factor Playbook.

Runs post-upload (background task). Per §10b.6 — slide raw text persisted to
sessions.slides_raw_text BEFORE LLM call so container restart survives.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from pptx import Presentation

from agents.llm import get_llm
from agents.schemas import SlideAnalysisBundle, SlideAnalysisPayload
from config import get_settings
from orchestrator.agno_orchestrator import AgnoOrchestrator

logger = logging.getLogger(__name__)

PLAYBOOK_PROMPT = """You evaluate a slide against the Tikal Presentation Skills Playbook.

Key factors (numbered, 1-12):
  1  Triangle of Alliances — slide supports the talk, not replaces it
  2  Trust / credibility — clarity of authorship + credentials
  3  Authenticity — original, not generic
  4  Keep it visual — limit text, use imagery instead of paragraphs
  5  10-20-30 rule — ~10 slides, font ≥30
  6  Use imagery — a picture is worth a thousand words
  7  Object count ≤6 per slide (cognitive load)
  8  Dark background + bright text (high contrast)
  9  Consistent fonts/header sizes
 10  Code display — animate or highlight, never overwhelm
 11  Speaker notes belong in notes area, not on slide
 12  Blank slides when you want all eyes on you

Reply JSON: {"findings": [{"slide_index": int (1-based), "playbook_factor": int (1-12),
"finding_type": "STRENGTH" | "IMPROVEMENT", "description": "short, actionable"}]}.
Aim for 5+ distinct factors covered across the deck."""


class PPTXAgent:
    def __init__(self, orchestrator: AgnoOrchestrator) -> None:
        self.orchestrator = orchestrator

    async def analyse(self, session_id: uuid.UUID, pptx_path: str) -> None:
        try:
            slides_raw = await asyncio.to_thread(self._extract_text, pptx_path)
        except Exception as exc:  # noqa: BLE001
            logger.exception("PPTX parse failed: %s", exc)
            return

        # Persist raw text immediately (§10b.6 — restart-safe)
        # Build empty bundle first to set slides_raw_text via Orchestrator.
        try:
            findings = await self._evaluate(slides_raw)
        except Exception as exc:  # noqa: BLE001
            logger.exception("PPTX LLM eval failed: %s", exc)
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
                logger.warning("invalid slide finding skipped: %s (%s)", raw, exc)
        return findings
