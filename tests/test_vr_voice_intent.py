"""Tests for the VR voice-intent endpoint (S26).

All HTTP calls to the LLM are mocked — no real API calls are made.
"""

import os
import sys
import types
import json

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import vr_api  # noqa: E402

client = TestClient(vr_api.app)


class _FakeResponse:
    def __init__(self, content):
        self._content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class _FakeAsyncClient:
    """Stand-in for httpx.AsyncClient that records calls and returns canned content."""

    calls = []
    content = ""
    raises = False

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        type(self).calls.append({"url": url, **kwargs})
        if type(self).raises:
            raise RuntimeError("upstream unavailable")
        return _FakeResponse(type(self).content)


@pytest.fixture
def fake_llm(monkeypatch):
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.content = ""
    _FakeAsyncClient.raises = False
    monkeypatch.setattr(vr_api, "httpx", types.SimpleNamespace(AsyncClient=_FakeAsyncClient))
    monkeypatch.setenv("META_API_KEY", "test-key")
    return _FakeAsyncClient


def test_interpret_voice_happy_path(fake_llm):
    """A well-formed LLM reply maps straight through to the intent object."""
    fake_llm.content = '{"intent": "approve_po", "item": "Widget-A"}'
    res = client.post("/api/vr/interpret-voice", json={"transcript": "approve the PO"})
    assert res.status_code == 200
    assert res.json() == {"intent": "approve_po", "item": "Widget-A"}
    assert len(fake_llm.calls) == 1
    assert fake_llm.calls[0]["url"].endswith("/chat/completions")
    assert fake_llm.calls[0]["json"]["model"] == "muse-spark-1.3"


def test_interpret_voice_fenced_json(fake_llm):
    """Markdown-fenced replies are parsed instead of falling through to unknown."""
    fake_llm.content = '```json\n{"intent": "restock", "item": null}\n```'
    res = client.post("/api/vr/interpret-voice", json={"transcript": "restock Widget-A"})
    assert res.json() == {"intent": "restock", "item": None}


def test_interpret_voice_prose_wrapped_json(fake_llm):
    """JSON embedded in prose is recovered by brace extraction."""
    fake_llm.content = 'Sure! {"intent": "pay_invoice", "item": "Widget-A"} hope that helps'
    res = client.post("/api/vr/interpret-voice", json={"transcript": "pay the invoice"})
    assert res.json() == {"intent": "pay_invoice", "item": "Widget-A"}


def test_interpret_voice_unknown_intent_is_coerced(fake_llm):
    """An intent outside the allowed vocabulary becomes 'unknown', never a crash."""
    fake_llm.content = '{"intent": "launch_missiles", "item": null}'
    res = client.post("/api/vr/interpret-voice", json={"transcript": "launch"})
    assert res.json() == {"intent": "unknown", "item": None}


def test_interpret_voice_no_api_key(monkeypatch):
    """Without a key the endpoint degrades to unknown and makes no HTTP call."""
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MUSE_API_KEY", raising=False)
    fake = _FakeAsyncClient
    fake.calls = []
    monkeypatch.setattr(vr_api, "httpx", types.SimpleNamespace(AsyncClient=fake))
    res = client.post("/api/vr/interpret-voice", json={"transcript": "restock"})
    assert res.json() == {"intent": "unknown", "item": None}
    assert fake.calls == []


def test_interpret_voice_upstream_error(fake_llm):
    """An upstream failure returns 200 + unknown instead of a 500 traceback."""
    fake_llm.raises = True
    res = client.post("/api/vr/interpret-voice", json={"transcript": "approve"})
    assert res.status_code == 200
    assert res.json() == {"intent": "unknown", "item": None}


def test_interpret_voice_empty_transcript(fake_llm):
    """Blank input short-circuits before any network call."""
    res = client.post("/api/vr/interpret-voice", json={"transcript": "   "})
    assert res.json() == {"intent": "unknown", "item": None}
    assert fake_llm.calls == []


def test_interpret_voice_missing_field(fake_llm):
    """A payload without 'transcript' still validates and returns unknown."""
    res = client.post("/api/vr/interpret-voice", json={})
    assert res.status_code == 200
    assert res.json() == {"intent": "unknown", "item": None}


@pytest.mark.parametrize(
    "content,expected",
    [
        ('{"intent": "restock", "item": "Widget-A"}', {"intent": "restock", "item": "Widget-A"}),
        ('```json\n{"intent":"show_invoice","item":null}\n```', {"intent": "show_invoice", "item": None}),
        ("no json here", {"intent": "unknown", "item": None}),
        ("", {"intent": "unknown", "item": None}),
        (None, {"intent": "unknown", "item": None}),
        ('{"intent": "REJECT_PO"}', {"intent": "reject_po", "item": None}),
        ('{"intent": "approve_po", "item": 42}', {"intent": "approve_po", "item": None}),
        ({"intent": "pay_invoice", "item": "Widget-A"}, {"intent": "pay_invoice", "item": "Widget-A"}),
    ],
)
def test_parse_intent_json(content, expected):
    """The parser normalizes casing, fences, dicts and non-string items."""
    assert vr_api._parse_intent_json(content) == expected


def test_agent_status_accepts_string_transcript():
    """Regression: a transcript seeded as plain strings must not raise a 500."""
    vr_api.execute_mutation(
        "INSERT OR REPLACE INTO agent_threads (thread_id, transcript, draft_po, status) VALUES (?,?,?,?)",
        ("test-string-transcript", json.dumps(["step one", "step two"]), "{}", "done"),
    )
    res = client.get("/api/vr/agent-status/test-string-transcript")
    assert res.status_code == 200
    assert res.json()["lines"] == ["step one", "step two"]


def test_shelf_scan_demo_matches_shelf_scene():
    """Regression: demo zones must agree with the static shelf quantities."""
    zones = {z["sku"]: z["qty"] for z in client.post("/api/vr/shelf-scan/demo").json()["zones"]}
    assert zones["Widget-A"] == 0
    assert zones["Widget-B"] == 3
    assert zones["Widget-C"] == 18
    assert zones["Widget-D"] == 24