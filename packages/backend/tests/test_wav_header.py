"""Verify B1 fix — raw PCM wrapped with RIFF/WAVE header decodes via stdlib `wave`."""

from __future__ import annotations

import io
import wave

from agents.audio_agent import _wrap_pcm_as_wav


def test_wrap_pcm_produces_decodable_wav():
    pcm = b"\x00\x00" * 16000  # 1 sec silence, 16-bit mono @ 16kHz
    wav_bytes = _wrap_pcm_as_wav(pcm, sample_rate=16000, channels=1, bits_per_sample=16)

    with wave.open(io.BytesIO(wav_bytes), "rb") as f:
        assert f.getframerate() == 16000
        assert f.getnchannels() == 1
        assert f.getsampwidth() == 2
        assert f.getnframes() == 16000

    # 44-byte header + payload
    assert len(wav_bytes) == 44 + len(pcm)
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"
