"""Verify WS handshake rejects bad token with close code 4003 (TECH-ARCH §5.6)."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _assert_4003(route: str, client: TestClient) -> None:
    fake_id = uuid.uuid4()
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"{route}?session_id={fake_id}&token=bogus"):
            pass
    assert exc.value.code == 4003


def test_ws_video_rejects_bad_token(client):
    _assert_4003("/video-stream", client)


def test_ws_audio_rejects_bad_token(client):
    _assert_4003("/audio-stream", client)


def test_ws_feedback_rejects_bad_token(client):
    _assert_4003("/realtime-feedback", client)


def test_ws_video_accepts_real_token(client):
    """Create a real session, connect with its token, send 1 frame, close cleanly."""
    resp = client.post("/sessions", json={"topic": "ws auth happy path test"})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    sid, tok = data["session_id"], data["access_token"]

    with client.websocket_connect(f"/video-stream?session_id={sid}&token={tok}") as ws:
        ws.send_bytes(b"\x00" * 16)
