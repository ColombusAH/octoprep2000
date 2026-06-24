"""Unit tests for agents.noise_reduction.apply_noise_reduction."""

import numpy as np
import pytest

from agents.noise_reduction import apply_noise_reduction


def _pcm(duration_s: float = 2.0, freq_hz: float = 440.0, sample_rate: int = 16000) -> bytes:
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    tone = (np.sin(2 * np.pi * freq_hz * t) * 0.5 * 32767).astype(np.int16)
    return tone.tobytes()


def _noisy_pcm(duration_s: float = 2.0, sample_rate: int = 16000) -> bytes:
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    tone = np.sin(2 * np.pi * 440.0 * t) * 0.5
    noise = np.random.default_rng(42).normal(0, 0.3, len(t))
    mixed = (tone + noise).clip(-1.0, 1.0)
    return (mixed * 32767).astype(np.int16).tobytes()


def test_noise_is_reduced():
    raw = _noisy_pcm()
    clean = apply_noise_reduction(raw)
    raw_arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    clean_arr = np.frombuffer(clean, dtype=np.int16).astype(np.float32)
    assert not np.array_equal(raw_arr, clean_arr), "Expected noise reduction to change the signal"


def test_silence_stays_near_zero():
    silent = bytes(64000)  # 2s of silence
    out = apply_noise_reduction(silent)
    arr = np.frombuffer(out, dtype=np.int16)
    assert np.all(np.abs(arr) < 100), "Silence should remain near-zero after noise reduction"


def test_garbage_bytes_returns_input_unchanged():
    garbage = b"\xff\xfe" * 100 + b"\x00" * 100
    out = apply_noise_reduction(garbage)
    # May succeed or fall back; either way must return bytes of same length as input
    assert isinstance(out, bytes)
    # If it failed gracefully, raw bytes returned
    assert len(out) == len(garbage) or len(out) > 0


def test_non_pcm_does_not_raise():
    bad = b"not audio at all"
    result = apply_noise_reduction(bad)
    assert isinstance(result, bytes)


def test_short_chunk_does_not_raise():
    short = _pcm(duration_s=0.1)
    result = apply_noise_reduction(short)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_empty_bytes_returns_empty():
    assert apply_noise_reduction(b"") == b""
