"""Slide WebSocket auth and happy-path smoke tests."""

from __future__ import annotations

import json
import uuid

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_ws_slide_rejects_bad_token(client):
    fake_id = uuid.uuid4()
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/slide-stream?session_id={fake_id}&token=bogus"):
            pass
    assert exc.value.code == 4003


def test_ws_slide_rejects_without_deck(client):
    resp = client.post("/sessions", json={"topic": "slide ws no deck test"})
    assert resp.status_code == 201
    data = resp.json()
    sid, tok = data["session_id"], data["access_token"]

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/slide-stream?session_id={sid}&token={tok}"):
            pass
    assert exc.value.code == 4000
