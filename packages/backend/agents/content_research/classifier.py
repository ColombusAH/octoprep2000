"""Topic classifier — determines if external research should run."""

from __future__ import annotations

from agno.agent import Agent
from loguru import logger
from pydantic import BaseModel, Field

from agents.content_research.reference_bundle import TopicClassification
from agents.llm import (
    call_with_fallback,
    get_text_model,
    get_text_model_fallback,
    pick_provider_order,
)

CLASSIFIER_PROMPT = """Classify whether a presentation session topic is TECHNICAL (domain-specific
factual accuracy and sub-topic coverage are meaningfully evaluable) or NON-TECHNICAL
(personal narrative, soft skills, career story without verifiable technical claims).

Return JSON with:
- is_technical: bool
- primary_libraries: up to 2 library/product names for documentation lookup (e.g. "react", "kubernetes")
- confidence: 0-1
- rationale: one short sentence
"""

CONFIDENCE_THRESHOLD = 0.6


class _ClassificationResult(BaseModel):
    is_technical: bool
    primary_libraries: list[str] = Field(default_factory=list, max_length=2)
    confidence: float = Field(ge=0, le=1)
    rationale: str = ""


async def classify_topic(topic: str, topic_context: str | None = None) -> TopicClassification:
    context_line = f"\nAdditional context: {topic_context}" if topic_context else ""
    prompt = f"Topic: {topic}{context_line}"

    agent = Agent(
        model=get_text_model(),
        instructions=CLASSIFIER_PROMPT,
        output_schema=_ClassificationResult,
    )

    async def _gateway():
        return await agent.arun(prompt)

    fb = get_text_model_fallback()

    async def _claude():
        return await Agent(
            model=fb, instructions=CLASSIFIER_PROMPT, output_schema=_ClassificationResult
        ).arun(prompt)

    try:
        result = await call_with_fallback(*pick_provider_order(_claude if fb else None, _gateway))
        cr = result.content
        libraries = [lib.strip() for lib in cr.primary_libraries if lib.strip()][:2]
        effective_technical = cr.is_technical and cr.confidence >= CONFIDENCE_THRESHOLD
        return TopicClassification(
            is_technical=effective_technical,
            primary_libraries=libraries if effective_technical else [],
            confidence=cr.confidence,
            rationale=cr.rationale,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Topic classifier failed, defaulting non-technical: {}", exc)
        return TopicClassification(
            is_technical=False,
            primary_libraries=[],
            confidence=0.0,
            rationale="classification failed",
        )
