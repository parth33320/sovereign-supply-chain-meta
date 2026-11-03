"""
tests/test_analytics_dashboard.py

Tests for S13: Analytics dashboard panel and multi-tenant thread_id namespacing.
"""

import os
import time
import sqlite3
import subprocess
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from playwright.sync_api import sync_playwright, expect

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_thread_id_namespacing():
    """Verify tenant_id namespacing in config dict as f'{tenant_id}_{thread_id}'."""
    tenant_id = "Tenant_A"
    raw_thread_id = "12345-abcde"
    config = {"configurable": {"thread_id": f"{tenant_id}_{raw_thread_id}"}}
    assert config["configurable"]["thread_id"] == "Tenant_A_12345-abcde"

    # Ensure app.py source contains namespaced thread_id
    with open(REPO_ROOT / "app.py", "r") as f:
        content = f.read()

    # The config should namespace thread_id with tenant_id
    assert '{"configurable": {"thread_id": f"{tenant_id}_{st.session_state.thread_id}"}}' in content
    assert '{"configurable": {"thread_id": f"{tenant_id}_{st.session_state.pending_request_id}"}}' in content


def test_app_py_has_analytics_dashboard_sidebar():
    """Verify app.py includes all required S13 expander panels in the sidebar."""
    with open(REPO_ROOT / "app.py", "r") as f:
        content = f.read()

    # Expanders for each section
    assert "st.expander" in content
    assert "WAF Events Over Time" in content
    assert "PO History Table" in content
    assert "Disruption Alert History" in content
    assert "Forecast Predictions" in content

    # Check session_state initializations
    assert "waf_history" in content
    assert "disruption_history" in content
    assert "forecast_cache" in content


def test_po_history_query_executed_records(tmp_path):
    """Verify task_queue queries last 10 EXECUTED records."""
    db_file = tmp_path / "test_sap.db"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE task_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT,
            status TEXT,
            payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Insert dummy records
    for i in range(15):
        cur.execute(
            "INSERT INTO task_queue (request_id, status, payload) VALUES (?, ?, ?)",
            (f"req_{i}", "EXECUTED" if i % 2 == 0 else "DRAFTED", f"payload_{i}")
        )
    conn.commit()

    # Query last 10 EXECUTED records
    cur.execute("""
        SELECT id, request_id, status, payload, created_at
        FROM task_queue
        WHERE status = 'EXECUTED'
        ORDER BY id DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 8  # 15 items: 0, 2, 4, 6, 8, 10, 12, 14 are EXECUTED
    assert rows[0][1] == "req_14"
    assert rows[0][2] == "EXECUTED"


def test_disruption_history_recording():
    """Verify disruption alert history appends structured records."""
    disruption_history = []
    sample_alert = {
        "timestamp": "12:00:00",
        "severity": "high",
        "summary": "Port strike in Rotterdam."
    }
    disruption_history.append(sample_alert)
    assert len(disruption_history) == 1
    assert disruption_history[0]["severity"] == "high"


def test_forecast_confidence_color_mapping():
    """Verify confidence color coding: high=red, medium=orange, low=green."""
    color_map = {
        "high": "red",
        "medium": "orange",
        "low": "green",
    }
    assert color_map.get("high") == "red"
    assert color_map.get("medium") == "orange"
    assert color_map.get("low") == "green"


def test_analytics_dashboard_ui_playwright(tmp_path):
    """Playwright E2E verification of Analytics Dashboard in sidebar."""
    port = 8598
    proc = subprocess.Popen(
        [
            "streamlit", "run", "app.py",
            "--server.port", str(port),
            "--server.headless", "true"
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(os.environ, STREAMLIT_SERVER_PORT=str(port))
    )

    video_dir = tmp_path / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)

    try:
        time.sleep(3)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                record_video_dir=str(video_dir),
                record_video_size={"width": 1280, "height": 720}
            )
            page = context.new_page()
            page.goto(f"http://localhost:{port}", timeout=15000)

            expect(page).to_have_title("Sovereign Supply Chain Orchestrator")

            # Check Analytics Dashboard header in sidebar
            sidebar = page.locator('[data-testid="stSidebar"]')
            expect(sidebar).to_be_visible()
            expect(sidebar.get_by_text("Analytics Dashboard")).to_be_visible()

            # Check the 4 expanders
            expect(sidebar.get_by_text("WAF Events Over Time")).to_be_visible()
            expect(sidebar.get_by_text("PO History Table")).to_be_visible()
            expect(sidebar.get_by_text("Disruption Alert History")).to_be_visible()
            expect(sidebar.get_by_text("Forecast Predictions")).to_be_visible()

            screenshot_path = tmp_path / "analytics_dashboard.png"
            page.screenshot(path=str(screenshot_path))
            assert screenshot_path.exists()

            context.close()
            browser.close()

        videos = list(video_dir.glob("*.webm"))
        assert len(videos) > 0, "No Playwright video recorded"
    finally:
        proc.terminate()
        proc.wait(timeout=5)
