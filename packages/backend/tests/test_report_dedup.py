"""Verify ReportAgent.deduplication layer per PRD §3.

Recurring filler words → ONE insight with timestamps[] array.
Recurring video events of same type → ONE body insight with timestamps[].
Recurring slide findings on same factor → ONE slide insight with slides[].
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from agents.report_agent import ReportAgent


@dataclass
class _FakeTranscript:
    start_ms: int
    end_ms: int
    text: str
    filler_flags: list[str] | None


@dataclass
class _FakeAudioWarning:
    timestamp_ms: int
    event_type: str
    severity: str = "MEDIUM"


@dataclass
class _FakeVideoEvent:
    timestamp_ms: int
    event_type: str
    severity: str = "MEDIUM"


@dataclass
class _FakeSlideAnalysis:
    slide_index: int
    playbook_factor: int
    finding_type: str
    description: str
    suggested_fix: str = ""


def test_voice_dedupes_fillers_into_single_insight():
    agent = ReportAgent()
    entries = [
        _FakeTranscript(0, 2000, "um yes", ["um"]),
        _FakeTranscript(2000, 4000, "uh actually", ["uh"]),
        _FakeTranscript(4000, 6000, "um and like", ["um", "like"]),
    ]
    insights, score = agent._score_voice(entries, [])
    improvements = [i for i in insights if i.type == "IMPROVEMENT"]
    assert len(improvements) == 1
    assert "'um' (2x)" in improvements[0].message
    assert "'like' (1x)" in improvements[0].message
    assert sorted(improvements[0].timestamps) == [0, 2000, 4000, 4000]
    assert score < 100


def test_voice_includes_pacing_warnings():
    agent = ReportAgent()
    entries = [_FakeTranscript(0, 2000, "all good here", [])]
    warnings = [
        _FakeAudioWarning(1000, "PACING_TOO_FAST"),
        _FakeAudioWarning(3000, "PACING_TOO_FAST"),
        _FakeAudioWarning(5000, "PACING_TOO_SLOW"),
    ]
    insights, score = agent._score_voice(entries, warnings)
    improvements = [i for i in insights if i.type == "IMPROVEMENT"]
    fast = next(i for i in improvements if "too fast" in i.message.lower())
    slow = next(i for i in improvements if "too slowly" in i.message.lower())
    assert sorted(fast.timestamps) == [1000, 3000]
    assert slow.timestamps == [5000]
    assert score < 100
    # No "steady pacing" strength claim when pacing issues were detected
    assert not any(i.type == "STRENGTH" for i in insights)


def test_body_groups_video_events_by_type():
    agent = ReportAgent()
    events = [
        _FakeVideoEvent(1000, "EYE_CONTACT_LOST"),
        _FakeVideoEvent(2500, "POSTURE_ISSUE"),
        _FakeVideoEvent(4000, "EYE_CONTACT_LOST"),
        _FakeVideoEvent(7000, "EYE_CONTACT_LOST"),
    ]
    insights, score = agent._score_body(events)
    by_type = {i.message.split(" (")[0]: i for i in insights}
    assert "Eye Contact Lost" in by_type
    assert sorted(by_type["Eye Contact Lost"].timestamps) == [1000, 4000, 7000]
    assert by_type["Eye Contact Lost"].message.endswith("(3x)")


def test_slides_group_by_factor_and_type():
    agent = ReportAgent()
    items = [
        _FakeSlideAnalysis(3, 4, "IMPROVEMENT", "Too much text"),
        _FakeSlideAnalysis(7, 4, "IMPROVEMENT", "Too much text"),
        _FakeSlideAnalysis(9, 4, "IMPROVEMENT", "Too much text"),
        _FakeSlideAnalysis(1, 8, "STRENGTH", "Clean title"),
    ]
    insights, _ = agent._score_slides(items)
    by_factor = {(i.type, tuple(i.slides)): i for i in insights}
    # Factor 4 IMPROVEMENT: slides 3, 7, 9 dedupe to one insight
    assert ("IMPROVEMENT", (3, 7, 9)) in by_factor
    # Factor 8 STRENGTH: single insight
    assert ("STRENGTH", (1,)) in by_factor


def test_slides_improvement_includes_suggested_fix_in_message():
    agent = ReportAgent()
    items = [
        _FakeSlideAnalysis(
            4,
            5,
            "IMPROVEMENT",
            "Slide 4 has 13 objects — above the ≤6 limit.",
            suggested_fix="Keep title + ≤3 bullets + one chart; delete the rest.",
        )
    ]
    insights, _ = agent._score_slides(items)
    assert len(insights) == 1
    assert "Instead:" in insights[0].message
    assert "Keep title" in insights[0].message


def test_slides_delivery_prefix_in_message():
    agent = ReportAgent()

    class _DeliverySlide:
        slide_index = 4
        playbook_factor = 1
        finding_type = "IMPROVEMENT"
        description = "Speech and slide content mismatched."
        suggested_fix = "Update slide 4 to match what you said."
        analysis_phase = "delivery"

    insights, _ = agent._score_slides([_DeliverySlide()])
    assert "While presenting:" in insights[0].message
    assert "Instead:" in insights[0].message


def test_slides_static_and_delivery_same_factor_not_merged():
    agent = ReportAgent()

    class _Static:
        slide_index = 4
        playbook_factor = 1
        finding_type = "IMPROVEMENT"
        description = "Too much text on slide."
        suggested_fix = "Cut bullets."
        analysis_phase = "static"

    class _Delivery:
        slide_index = 4
        playbook_factor = 1
        finding_type = "IMPROVEMENT"
        description = "Speech mismatched slide at 2:15."
        suggested_fix = "Update slide content."
        analysis_phase = "delivery"

    insights, _ = agent._score_slides([_Static(), _Delivery()])
    assert len(insights) == 2
    messages = {i.message for i in insights}
    assert any("While presenting:" in m for m in messages)
    assert any("While presenting:" not in m for m in messages)


def test_smile_strong_surfaces_as_strength_not_penalty():
    agent = ReportAgent()
    events = [
        _FakeVideoEvent(1000, "SMILING_STRONG", severity="LOW"),
        _FakeVideoEvent(2000, "POSTURE_ISSUE"),
    ]
    insights, score = agent._score_body(events)
    strengths = [i for i in insights if i.type == "STRENGTH"]
    improvements = [i for i in insights if i.type == "IMPROVEMENT"]
    assert len(strengths) == 1
    assert "smiling" in strengths[0].message.lower()
    # Only POSTURE_ISSUE counts toward penalty
    assert score == 98.0  # 100 - 1*2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
