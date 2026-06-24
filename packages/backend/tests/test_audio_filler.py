from __future__ import annotations

from agents.audio_agent import _detect_fillers


def test_detect_fillers_matches_obvious_um_and_uh_boundaries():
    assert _detect_fillers("Um, this is not yummy. Uh, next point.") == ["um", "uh"]


def test_detect_fillers_does_not_penalize_single_ambiguous_like():
    assert _detect_fillers("So like, the React Compiler is one headline feature.") == []


def test_detect_fillers_counts_repeated_ambiguous_like():
    assert _detect_fillers("Like, this is like the key tradeoff.") == ["like", "like"]
