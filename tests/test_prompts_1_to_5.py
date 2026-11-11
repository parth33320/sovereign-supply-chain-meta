"""Tests for Prompt 1 - 5 features."""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
import cancel_registry
from graph import a2a_negotiate_sync, draft_po
from demand_forecaster import calculate_sku_reorder_point, forecast_sku_stockouts
from voice_handler import process_voice_input, suggest_voice_intent

os.environ["DEMO_MODE"] = "1"
client = TestClient(app)


def test_cancel_registry_lifecycle():
    thread_id = "test-thread-lifecycle"
    event = cancel_registry.register(thread_id)
    assert not cancel_registry.is_cancelled(thread_id)
    assert not event.is_set()

    cancel_registry.cancel(thread_id)
    assert cancel_registry.is_cancelled(thread_id)
    assert event.is_set()

    cancel_registry.cleanup(thread_id)
    assert not cancel_registry.is_cancelled(thread_id)


def test_delete_chat_cancel_endpoint():
    thread_id = "cancel-endpoint-thread"
    cancel_registry.register(thread_id)
    res = client.delete(f"/api/chat/{thread_id}")
    assert res.status_code == 200
    assert res.json() == {"status": "cancelled"}
    assert cancel_registry.is_cancelled(thread_id)
    cancel_registry.cleanup(thread_id)


def test_chat_stream_and_progress_events():
    res = client.post("/api/chat/stream", json={
        "message": "Check inventory levels",
        "thread_id": "stream-thread-1",
        "tenant_id": "Tenant_A"
    })
    assert res.status_code == 200
    text = res.text
    assert "data: " in text
    assert "global_oracle" in text or "complete" in text


def test_chat_stream_cancellation():
    thread_id = "stream-cancel-thread"
    cancel_registry.register(thread_id)
    cancel_registry.cancel(thread_id)

    res = client.post("/api/chat/stream", json={
        "message": "Check stock levels for Widget-A",
        "thread_id": thread_id,
        "tenant_id": "Tenant_A"
    })
    assert res.status_code == 200
    assert '{"node": "cancelled", "label": "Request cancelled."}' in res.text


def test_voice_history_endpoint_and_logging():
    # Submit a voice recording
    with patch("voice_handler.process_voice_input", return_value={"status": "ok", "transcription": "Emergency restock Widget-A"}):
        res = client.post(
            "/api/voice",
            files={"file": ("recording.wav", b"RIFF0000WAVEfmt ", "audio/wav")},
            data={"thread_id": "vh-thread-1", "source": "upload"}
        )
    assert res.status_code == 200

    # Fetch voice history
    h_res = client.get("/api/voice/history")
    assert h_res.status_code == 200
    history = h_res.json()
    assert isinstance(history, list)
    assert len(history) > 0
    assert any("Widget-A" in h["transcript"] or len(h["transcript"]) > 0 for h in history)


def test_duplicate_invoice_detection():
    data = b"INVOICE-PDF-CONTENT-SAMPLE-UNIQUE-TEST"
    # First upload
    res1 = client.post(
        "/api/upload",
        files={"file": ("invoice-1.pdf", data, "application/pdf")}
    )
    assert res1.status_code in [200, 409]

    # Second upload should detect duplicate
    res2 = client.post(
        "/api/upload",
        files={"file": ("invoice-1.pdf", data, "application/pdf")}
    )
    assert res2.status_code == 409
    err_data = res2.json()
    assert "Duplicate invoice detected" in err_data.get("error", "")
    assert "first_seen" in err_data


def test_competitive_multi_supplier_rfq():
    state = {
        "tenant_id": "Tenant_A",
        "request_id": "rfq-test",
        "inventory_data": [{"name": "Widget-A", "quantity": 0}],
        "messages": [],
        "a2a_transcript": []
    }
    rfq_res = a2a_negotiate_sync(state)
    quotes = rfq_res.get("supplier_quotes", [])
    assert len(quotes) == 3
    suppliers = [q.get("supplier") for q in quotes]
    assert "Apex Logistics" in suppliers
    assert "Global Parts Co" in suppliers
    assert "FastShip Supply" in suppliers

    assert "analyst_recommendation" in rfq_res
    state.update(rfq_res)
    po_res = draft_po(state)
    po = po_res.get("pending_po", {})
    assert len(po.get("quotes", [])) == 3
    assert "recommendation" in po


def test_whatif_scenario_endpoint():
    res = client.post("/api/whatif", json={
        "scenario": "Supplier Apex Logistics is offline for 10 days",
        "thread_id": "whatif-test",
        "tenant_id": "Tenant_A"
    })
    assert res.status_code == 200
    body = res.json()
    assert "affected_skus" in body
    assert len(body["affected_skus"]) > 0
    assert "summary" in body


def test_kpi_dashboard_endpoint():
    res = client.get("/api/kpi?tenant_id=Tenant_A")
    assert res.status_code == 200
    kpis = res.json()
    assert "stockout_rate" in kpis
    assert "fill_rate" in kpis
    assert "low_stock_rate" in kpis
    assert "summary" in kpis
    assert kpis.get("risk_rating") in ["green", "yellow", "red"]


def test_reorder_point_calculation():
    res = calculate_sku_reorder_point("Widget-A", 50, transit_time=4)
    assert "reorder_point" in res
    assert "eoq" in res
    assert res["reorder_point"] > 0
    assert res["eoq"] > 0


def test_voice_confidence_gating():
    # Low confidence mock input
    res = process_voice_input(b"short", source="upload", filename="sample-voice.wav")
    assert "transcription" in res

    # Test suggestion generation
    sug = suggest_voice_intent("restock microcontrollers")
    assert len(sug) > 0
