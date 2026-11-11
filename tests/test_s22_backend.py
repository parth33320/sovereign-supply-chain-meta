"""Tests for Sprint S22 FastAPI backend."""

import os
import sys
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.main import app

client = TestClient(app)

def test_health_returns_200():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_chat_endpoint_exists():
    with patch("backend.routers.chat.run_graph") as mock:
        mock.return_value = {"messages": [], "status": "executed"}
        r = client.post(
            "/api/chat",
            json={
                "message": "Check stock Widget-A",
                "thread_id": "test-123",
                "tenant_id": "Tenant_A",
            },
        )
        assert r.status_code == 200
        assert "response" in r.json()

def test_chat_blocked_by_guardrail():
    with patch("backend.routers.chat.check_prompt_injection", return_value=False):
        r = client.post(
            "/api/chat",
            json={
                "message": "DROP TABLE inventory",
                "thread_id": "test-123",
                "tenant_id": "Tenant_A",
            },
        )
        assert r.status_code == 200
        assert r.json()["blocked"] is True

def test_upload_endpoint_accepts_image():
    with patch("backend.routers.upload.classify_image", return_value="shelf"):
        with patch(
            "backend.routers.upload.analyze_shelf_image",
            return_value={"segments": [], "summary": "ok"},
        ):
            with open("demo-assets/sample_shelf.jpg", "rb") as f:
                r = client.post(
                    "/api/upload", files={"file": ("shelf.jpg", f, "image/jpeg")}
                )
            assert r.status_code == 200
            assert r.json()["type"] == "shelf"

def test_upload_endpoint_accepts_audio():
    with patch(
        "backend.routers.voice.transcribe_audio",
        return_value="Check stock Widget-A",
    ):
        with open("demo-assets/sample_voice_command.wav", "rb") as f:
            r = client.post(
                "/api/voice", files={"file": ("cmd.wav", f, "audio/wav")}
            )
        assert r.status_code == 200
        assert "transcript" in r.json()

def test_hitl_approve():
    with patch("backend.routers.hitl.resume_graph") as mock:
        mock.return_value = {"status": "executed"}
        r = client.post(
            "/api/hitl/approve",
            json={"thread_id": "test-123", "tenant_id": "Tenant_A"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

def test_hitl_reject():
    r = client.post(
        "/api/hitl/reject",
        json={"thread_id": "test-123", "tenant_id": "Tenant_A"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"

def test_activity_sse_endpoint_exists():
    with client.stream("GET", "/api/activity/stream?thread_id=test-123") as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]

def test_static_files_served():
    if os.path.exists("frontend/dist/index.html"):
        r = client.get("/")
        assert r.status_code == 200

def test_upload_shelf_routed_by_filename():
    with patch("backend.routers.upload.analyze_shelf_image", return_value={"segments": [], "summary": "shelf ok"}):
        r = client.post(
            "/api/upload",
            files={"file": ("sample-shelf.png", b"\x89PNG\r\n\x1a\nfake", "image/png")}
        )
        assert r.status_code == 200
        assert r.json()["type"] == "shelf"

def test_upload_invoice_routed_by_filename():
    with patch("backend.routers.upload.extract_document_data", return_value={"supplier": "Test Corp"}):
        r = client.post(
            "/api/upload",
            files={"file": ("invoice.png", b"\x89PNG\r\n\x1a\nfake", "image/png")}
        )
        assert r.status_code == 200
        assert r.json()["type"] == "invoice"

def test_upload_sample_voice_wav_demo_fallback():
    r = client.post(
        "/api/upload",
        files={"file": ("sample-voice.wav", b"RIFF....WAVE", "audio/wav")}
    )
    assert r.status_code == 200
    assert r.json()["type"] == "audio"
    assert "Widget-A" in r.json()["transcript"]
