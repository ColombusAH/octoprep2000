"""ContentAnalysisAgent — post-session technical accuracy + coverage gap analysis.

Reads transcript from DB (read-only) + session topic. Emits ContentAnalysisPayload.
Uses get_session_maker() to own its own AsyncSession (decoupled from request scope).
"""

from __future__ import annotations

import uuid

from agno.agent import Agent
from loguru import logger

from agents.llm import (
    call_with_fallback,
    get_text_model,
    get_text_model_fallback,
    pick_provider_order,
)
from agents.replay_fixtures import replay_content_analysis
from agents.schemas import ContentAnalysisPayload, ContentResult
from config import get_settings
from db.repository import PostgreSQLRepository
from db.session import get_session_maker

CONTENT_PROMPT = """You evaluate a presenter's transcript for technical accuracy and coverage
against the stated topic. Return JSON:
{"content_score": int (0-100), "findings": [
  {"type": "FACTUAL_ERROR" | "COVERAGE_GAP" | "STRENGTH",
   "message": "short, specific",
   "context_quote": "verbatim phrase from transcript (or empty for COVERAGE_GAP)"}
]}.
Disclose uncertainty for topics that may post-date training cutoff."""


class ContentAnalysisAgent:
    async def analyse(self, session_id: uuid.UUID) -> ContentAnalysisPayload | None:
        async with get_session_maker()() as db:
            repo = PostgreSQLRepository(db)
            session = await repo.get_session(session_id)
            if not session:
                return None
            entries = await repo.read_transcript(session_id)

        if get_settings().demo_replay:
            return replay_content_analysis(session_id, session.topic)

        transcript = " ".join(e.text for e in entries).strip()
        if not transcript:
            return ContentAnalysisPayload(
                session_id=session_id,
                topic=session.topic,
                content_score=0,
                findings=[],
            )

        prompt = f"Topic: {session.topic}\n\nTranscript:\n{transcript[:12000]}"
        agent = Agent(
            model=get_text_model(),
            instructions=CONTENT_PROMPT,
            output_schema=ContentResult,
        )

        async def _gateway():
            return await agent.arun(prompt)

        fb = get_text_model_fallback()

        async def _claude():
            return await Agent(model=fb, instructions=CONTENT_PROMPT, output_schema=ContentResult).arun(prompt)

        claude_fn = _claude if fb else None
        primary, secondary = pick_provider_order(claude_fn, _gateway)
        try:
            result = await call_with_fallback(primary, secondary)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Content LLM failed: {}", exc)
            return None

        cr = result.content
        logger.info("Content LLM result: score={} findings={}", cr.content_score, len(cr.findings))
        return ContentAnalysisPayload(
            session_id=session_id,
            topic=session.topic,
            content_score=float(max(0, min(100, cr.content_score))),
            findings=cr.findings,
        )
