"""PptxPrepWorkflow — pre-session agno Workflow (one-shot, off the real-time path).

Four genuine steps mirroring the durability ordering:
  extract  → parse the deck to structured slide rows
  review   → evaluate against the Tikal 12-factor playbook (LLM, or replay fixtures)
  research → gather topic reference material (Context7/Exa) for reuse at report time
  write    → persist slide_analyses + research + mark_pptx_ready (+ notify_complete("PPTX"))

Research runs BEFORE write so the session-start gate (frontend polls pptx_ready, which
only flips in write) waits for research — no rehearsal-vs-research race (feature 002).
Each step delegates to a PPTXAgent phase, so the agent still owns its writes (Principle II).
"""

from __future__ import annotations

import uuid

from agno.workflow import Step, Workflow
from agno.workflow.types import StepInput, StepOutput
from loguru import logger

from agents.pptx_agent import PPTXAgent
from orchestrator.orchestrator import Orchestrator


async def run_pptx_prep_workflow(
    orchestrator: Orchestrator,
    session_id: uuid.UUID,
    pptx_path: str,
    speech_language: str = "en",
    deck_language: str = "en",
) -> None:
    agent = PPTXAgent(orchestrator)
    ctx: dict = {"bundle": None, "research_status": "not_applicable"}

    async def extract_step(_si: StepInput) -> StepOutput:
        ctx["slides_raw"] = await agent.extract(pptx_path)
        return StepOutput(content=f"extracted {len(ctx['slides_raw'])} slide(s)")

    async def review_step(_si: StepInput) -> StepOutput:
        ctx["findings"] = await agent.review(ctx["slides_raw"], speech_language, deck_language)
        return StepOutput(content=f"{len(ctx['findings'])} finding(s)")

    async def research_step(_si: StepInput) -> StepOutput:
        # Must never abort the workflow: a research failure still leaves write to run
        # and mark the deck ready (FR-006/FR-007 resilience).
        try:
            session = await agent._with_repo(lambda r: r.get_session(session_id))
            if session is not None:
                ctx["bundle"], ctx["research_status"] = await agent.research(
                    session.topic, session.topic_context
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("PPTX pre-session research failed: {}", exc)
            ctx["bundle"], ctx["research_status"] = None, "skipped"
        return StepOutput(content=f"research: {ctx['research_status']}")

    async def write_step(_si: StepInput) -> StepOutput:
        await agent.persist(
            session_id,
            ctx["slides_raw"],
            ctx["findings"],
            bundle=ctx["bundle"],
            research_status=ctx["research_status"],
        )
        return StepOutput(content="slide_analyses + research written")

    workflow = Workflow(
        name="pptx-prep",
        telemetry=False,
        db=None,
        steps=[
            Step(name="extract", executor=extract_step),
            Step(name="review", executor=review_step),
            Step(name="research", executor=research_step),
            Step(name="write", executor=write_step),
        ],
    )
    await workflow.arun(input=str(session_id))
