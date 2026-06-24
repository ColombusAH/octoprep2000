from __future__ import annotations

import uuid

from agents.replay_fixtures import replay_audio_events
from agents.schemas import AudioWarningPayload, TranscriptPayload


def test_replay_audio_events_do_not_mutate_cached_fixture_rows():
    session_id = uuid.uuid4()

    first = replay_audio_events(session_id)
    second = replay_audio_events(session_id)

    assert sum(isinstance(ev, TranscriptPayload) for ev in first) == 4
    assert sum(isinstance(ev, AudioWarningPayload) for ev in first) == 2
    assert sum(isinstance(ev, TranscriptPayload) for ev in second) == 4
    assert sum(isinstance(ev, AudioWarningPayload) for ev in second) == 2
