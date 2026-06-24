"""ReportWorkflow delivery step — Phase B slide_events integration."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.report_agent import ReportAgent
from agents.replay_fixtures import replay_slide_events


def _session_with_deck():
    return SimpleNamespace(
        topic="React 19 features",
        topic_context="Senior devs",
        slides_raw_text=[{"slide_index": 1, "text": "Intro"}],
    )


def _transcript():
    return [SimpleNamespace(start_ms=0, end_ms=2000, text="Today we cover React 19.")]


@pytest.mark.asyncio
async def test_run_delivery_passes_db_slide_events_to_analyse_delivery():
    agent = ReportAgent(orchestrator=AsyncMock())
    session_id = uuid.uuid4()
    slide_events = [SimpleNamespace(slide_index=1, timestamp_ms=0, source="manual")]
    inputs = {"session": _session_with_deck(), "transcripts": _transcript()}

    mock_repo = AsyncMock()
    mock_repo.read_slide_events = AsyncMock(return_value=slide_events)
    mock_db = AsyncMock()

    mock_pptx = AsyncMock()
    mock_pptx.analyse_delivery = AsyncMock()

    with patch("agents.report_agent.get_session_maker") as mock_sm, patch(
        "agents.report_agent.PostgreSQLRepository", return_value=mock_repo
    ), patch("agents.report_agent.PPTXAgent", return_value=mock_pptx) as MockPPTX, patch(
        "agents.report_agent.get_settings"
    ) as mock_settings:
        mock_settings.return_value.demo_replay = False
        mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

        await agent.run_delivery(session_id, inputs, content=None)

    mock_pptx.analyse_delivery.assert_awaited_once()
    assert mock_pptx.analyse_delivery.await_args.kwargs["slide_events"] == slide_events
    MockPPTX.assert_called_once_with(agent.orchestrator, session_id=session_id)


@pytest.mark.asyncio
async def test_run_delivery_replay_fallback_when_db_has_no_events():
    agent = ReportAgent(orchestrator=AsyncMock())
    session_id = uuid.uuid4()
    inputs = {"session": _session_with_deck(), "transcripts": _transcript()}
    replay_events = replay_slide_events()

    mock_repo = AsyncMock()
    mock_repo.read_slide_events = AsyncMock(return_value=[])
    mock_db = AsyncMock()

    mock_pptx = AsyncMock()
    mock_pptx.analyse_delivery = AsyncMock()

    with patch("agents.report_agent.get_session_maker") as mock_sm, patch(
        "agents.report_agent.PostgreSQLRepository", return_value=mock_repo
    ), patch("agents.report_agent.PPTXAgent", return_value=mock_pptx), patch(
        "agents.report_agent.get_settings"
    ) as mock_settings:
        mock_settings.return_value.demo_replay = True
        mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

        await agent.run_delivery(session_id, inputs, content=None)

    passed = mock_pptx.analyse_delivery.await_args.kwargs["slide_events"]
    assert len(passed) == len(replay_events)
    assert passed[0].slide_index == replay_events[0].slide_index


@pytest.mark.asyncio
async def test_report_workflow_delivery_step_delegates_to_run_delivery():
    """ReportWorkflow delivery step must call ReportAgent.run_delivery (not inline generate)."""
    agent = ReportAgent(orchestrator=AsyncMock())
    session_id = uuid.uuid4()
    payload = MagicMock()

    agent.read_inputs = AsyncMock(
        return_value={
            "session": _session_with_deck(),
            "transcripts": _transcript(),
            "video_events": [],
            "audio_warnings": [],
        }
    )
    agent.content_agent.analyse = AsyncMock(return_value=None)
    agent.run_delivery = AsyncMock()
    agent.assemble_and_write = AsyncMock(return_value=payload)

    from workflows.report import run_report_workflow

    result = await run_report_workflow(agent, session_id, fallback_mode=False)

    agent.run_delivery.assert_awaited_once()
    assert agent.run_delivery.await_args.args[0] == session_id
    assert result is payload
