"""S24 UX Fixes unit tests."""

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys, os, io

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.main import app

client = TestClient(app)


def test_upload_shelf_demo_mode_returns_valid_json():
    # Must never return 500 or error when DEMO_MODE=1
    os.environ["DEMO_MODE"] = "1"
    img = open("demo-assets/sample_shelf.jpg", "rb").read()
    with patch(
        "backend.routers.upload.analyze_shelf_image",
        return_value={
            "segments": [
                {"label": "Widget-A", "fill_pct": 20, "status": "LOW"}
            ],
            "summary": "1 low stock item detected",
        },
    ):
        r = client.post(
            "/api/upload", files={"file": ("shelf.jpg", img, "image/jpeg")}
        )
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "shelf"
    assert "analysis" in data
    assert data.get("error") is None or "error" not in data


def test_upload_invoice_demo_mode_returns_valid_json():
    os.environ["DEMO_MODE"] = "1"
    img = open("demo-assets/sample_invoice.png", "rb").read()
    with patch("backend.routers.upload.classify_image", return_value="invoice"):
        with patch(
            "backend.routers.upload.extract_document_data",
            return_value={
                "supplier": "FastFreight Ltd",
                "total": "$4,500.00",
                "items": [],
            },
        ):
            r = client.post(
                "/api/upload",
                files={"file": ("invoice.png", img, "image/png")},
            )
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "invoice"
    assert "extraction" in data


def test_upload_api_failure_returns_friendly_error():
    # When Meta API fails, must return 200 with error message
    # not 500 crash
    os.environ["DEMO_MODE"] = "0"
    img = open("demo-assets/sample_shelf.jpg", "rb").read()
    with patch("backend.routers.upload.classify_image", return_value="shelf"):
        with patch(
            "backend.routers.upload.analyze_shelf_image",
            side_effect=Exception("Meta API unavailable"),
        ):
            r = client.post(
                "/api/upload", files={"file": ("shelf.jpg", img, "image/jpeg")}
            )
    assert r.status_code == 200
    data = r.json()
    assert "error" in data
    assert data["error"] is not None
    # Must never be a 500 internal server error


def test_upload_audio_demo_mode_returns_transcript():
    with patch(
        "backend.routers.upload.transcribe_audio",
        return_value="Emergency restock Widget-A",
    ):
        wav = open("demo-assets/sample_voice_command.wav", "rb").read()
        r = client.post(
            "/api/upload", files={"file": ("cmd.wav", wav, "audio/wav")}
        )
    assert r.status_code == 200
    assert r.json()["type"] == "audio"
    assert r.json()["transcript"] == "Emergency restock Widget-A"
