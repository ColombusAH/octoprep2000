"""ContentAnalysisAgent — post-session technical accuracy + coverage gap analysis.

Reads transcript from DB (read-only) + session topic. Emits ContentAnalysisPayload.
Uses get_session_maker() to own its own AsyncSession (decoupled from request scope).
"""

from __future__ import annotations

import json
from loguru import logger
import uuid

from agents.llm import get_llm
from agents.replay_fixtures import replay_content_analysis
from agents.schemas import ContentAnalysisPayload, ContentFinding
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

        s = get_settings()
        client = get_llm()
        prompt = f"Topic: {session.topic}\n\nTranscript:\n{transcript[:12000]}"
        try:
            resp = await client.chat.completions.create(
                model=s.litellm_text_model,
                messages=[
                    {"role": "system", "content": CONTENT_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=1500,
            )
            data = json.loads(resp.choices[0].message.content or "{}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Content LLM failed: {}", exc)
            return None

        findings = []
        for raw in data.get("findings", []):
            try:
                findings.append(ContentFinding(**raw))
            except Exception as exc:  # noqa: BLE001
                logger.warning("invalid content finding skipped: {} ({})", raw, exc)

        return ContentAnalysisPayload(
            session_id=session_id,
            topic=session.topic,
            content_score=float(max(0, min(100, data.get("content_score", 0)))),
            findings=findings,
        )
