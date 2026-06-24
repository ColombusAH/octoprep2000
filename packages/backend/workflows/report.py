"""ReportWorkflow — end-of-session agno Workflow (off the real-time path).

A sequential pipeline of genuine data dependencies — there is nothing to route or
synthesize, so this is a Workflow of Steps, not a coordinator Team:

  read     → read the agreed tables the live agents wrote (Principle II read side)
  content  → ContentAgent technical-accuracy / coverage analysis (the "Insight" pass)
  delivery → PPTX delivery pass, which CONSUMES the content findings
  score    → deterministic Python scoring (unchanged) + the agent-owned reports write

Each step delegates to a ReportAgent phase. agno glue only: telemetry=False, db=None.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from agno.workflow import Step, Workflow
from agno.workflow.types import StepInput, StepOutput

if TYPE_CHECKING:
    from agents.report_agent import ReportAgent
    from agents.schemas import ReportPayload


async def run_report_workflow(
    agent: ReportAgent,
    session_id: uuid.UUID,
    fallback_mode: bool = False,
    speech_language: str = "en",
) -> ReportPayload:
    ctx: dict = {}

    async def read_step(_si: StepInput) -> StepOutput:
        ctx["inputs"] = await agent.read_inputs(session_id)
        return StepOutput(content="read agreed tables")

    async def content_step(_si: StepInput) -> StepOutput:
        ctx["content"] = await agent.content_agent.analyse(session_id)
        return StepOutput(content="content analysed")

    async def delivery_step(_si: StepInput) -> StepOutput:
        await agent.run_delivery(session_id, ctx["inputs"], ctx["content"])
        return StepOutput(content="delivery pass done")

    async def score_step(_si: StepInput) -> StepOutput:
        ctx["payload"] = await agent.assemble_and_write(
            session_id, ctx["inputs"], ctx["content"], fallback_mode, speech_language
        )
        return StepOutput(content="report written")

    workflow = Workflow(
        name="report",
        telemetry=False,
        db=None,
        steps=[
            Step(name="read", executor=read_step),
            Step(name="content", executor=content_step),
            Step(name="delivery", executor=delivery_step),
            Step(name="score", executor=score_step),
        ],
    )
    await workflow.arun(input=str(session_id))
    return ctx["payload"]
