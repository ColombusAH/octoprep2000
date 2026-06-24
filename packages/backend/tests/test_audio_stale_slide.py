"""AudioAgent STALE_SLIDE live warning."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from agents.audio_agent import AudioAgent
from agents.schemas import AudioWarningPayload


@pytest.mark.asyncio
async def test_stale_slide_warning_emitted():
    orch = AsyncMock()
    warnings: list[AudioWarningPayload] = []

    def slide_state(_ts_ms: int):
        return {"slide_index": 4, "since_ms": 0, "dwell_ms": 250_000}

    agent = AudioAgent(uuid.uuid4(), orch, slide_state_provider=slide_state)
    agent._last_warning_ts = 0

    async def capture_warning(payload: AudioWarningPayload):
        warnings.append(payload)

    with patch.object(agent, "_write_warning", side_effect=capture_warning), patch(
        "agents.audio_agent.get_settings"
    ) as mock_settings:
        mock_settings.return_value.stale_slide_seconds = 240
        await agent._check_stale_slide(250_000)

    assert len(warnings) == 1
    assert warnings[0].event_type == "STALE_SLIDE"
    assert warnings[0].metadata == {"slide_index": 4, "dwell_ms": 250_000}
    assert "slide 4" in warnings[0].message.lower()
