"""PptxPrepWorkflow — pre-session agno Workflow (one-shot, off the real-time path).

Three genuine steps mirroring the durability ordering:
  extract  → parse the deck to structured slide rows
  review   → evaluate against the Tikal 12-factor playbook (LLM, or replay fixtures)
  write    → persist slide_analyses + mark_pptx_ready (+ notify_complete("PPTX"))

Each step delegates to a PPTXAgent phase, so the agent still owns its writes (Principle II).
"""

from __future__ import annotations

import uuid

from agno.workflow import Step, Workflow
from agno.workflow.types import StepInput, StepOutput

from agents.pptx_agent import PPTXAgent
from orchestrator.orchestrator import Orchestrator


async def run_pptx_prep_workflow(
    orchestrator: Orchestrator, session_id: uuid.UUID, pptx_path: str
) -> None:
    agent = PPTXAgent(orchestrator)
    ctx: dict = {}

    async def extract_step(_si: StepInput) -> StepOutput:
        ctx["slides_raw"] = await agent.extract(pptx_path)
        return StepOutput(content=f"extracted {len(ctx['slides_raw'])} slide(s)")

    async def review_step(_si: StepInput) -> StepOutput:
        ctx["findings"] = await agent.review(ctx["slides_raw"])
        return StepOutput(content=f"{len(ctx['findings'])} finding(s)")

    async def write_step(_si: StepInput) -> StepOutput:
        await agent.persist(session_id, ctx["slides_raw"], ctx["findings"])
        return StepOutput(content="slide_analyses written")

    workflow = Workflow(
        name="pptx-prep",
        telemetry=False,
        db=None,
        steps=[
            Step(name="extract", executor=extract_step),
            Step(name="review", executor=review_step),
            Step(name="write", executor=write_step),
        ],
    )
    await workflow.arun(input=str(session_id))
