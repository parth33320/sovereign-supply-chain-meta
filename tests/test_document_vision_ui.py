import os
import time
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from playwright.sync_api import sync_playwright, expect

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def mock_graph_deps():
    mock_graph = MagicMock()
    mock_state = MagicMock()
    mock_state.next = ()
    mock_graph.get_state.return_value = mock_state

    with patch("graph.get_graph_with_postgres", return_value=mock_graph):
        yield


def test_app_document_upload_tab_and_uploader_exists():
    """Test that app.py contains the Documents module with the image uploader."""
    import streamlit.testing.v1 as st_test
    app_path = REPO_ROOT / "app.py"
    at = st_test.AppTest.from_file(str(app_path), default_timeout=10)
    at.run()

    # Navigate to Documents module
    at.sidebar.radio[0].set_value("Documents")
    at.run()

    # Find the document uploader by key or label
    uploaders = [u for u in at.file_uploader if u.key == "document_image_uploader"]
    assert len(uploaders) == 1
    assert "Invoice" in uploaders[0].label or "Document" in uploaders[0].label


def test_app_document_upload_and_prepopulates_chat():
    """Test document upload extracts fields, shows extracted data, and prepopulates chat."""
    import streamlit.testing.v1 as st_test
    fake_img = b"\x89PNG\r\n\x1a\n"

    mock_doc_data = {
        "supplier": "Acme Global",
        "dates": ["2025-05-10"],
        "items": [
            {"description": "Steel Bearings", "quantity": 50, "unit_price": 10.0}
        ],
        "raw_summary": "Invoice for 50 steel bearings."
    }

    with patch("document_vision.extract_document_data", return_value=mock_doc_data) as mock_extract, \
         patch("worker.process_agent_task.delay") as mock_delay, \
         patch("celery.result.AsyncResult") as mock_async_result, \
         patch("guardrails.check_prompt_injection", return_value=True):

        mock_task = MagicMock()
        mock_task.id = "mock-task-doc-1"
        mock_delay.return_value = mock_task

        mock_async_task = MagicMock()
        mock_async_task.state = "PENDING"
        mock_async_result.return_value = mock_async_task

        app_path = REPO_ROOT / "app.py"
        at = st_test.AppTest.from_file(str(app_path), default_timeout=10)
        at.run()

        # Navigate to Documents module
        at.sidebar.radio[0].set_value("Documents")
        at.run()

        # Find document uploader and upload
        doc_uploader = [u for u in at.file_uploader if u.key == "document_image_uploader"][0]
        doc_uploader.upload("invoice.png", fake_img)
        at.run()

        mock_extract.assert_called_once_with(fake_img)
        assert at.session_state["extracted_document"] == mock_doc_data
        assert "prefilled_prompt" in at.session_state
        assert "Acme Global" in at.session_state["prefilled_prompt"]
        assert "50x Steel Bearings" in at.session_state["prefilled_prompt"]


def test_document_vision_ui_e2e_playwright(tmp_path):
    """Playwright E2E verification of Documents module and extraction readout."""
    port = 8599
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

            expect(page).to_have_title("Sovereign Supply Chain Orchestrator", timeout=15000)

            # Click "Documents" in sidebar navigation rail
            sidebar = page.locator('[data-testid="stSidebar"]')
            expect(sidebar).to_be_visible()

            doc_nav = sidebar.locator('label', has_text="Documents")
            expect(doc_nav).to_be_visible()
            doc_nav.click()
            time.sleep(1)

            # Verify document uploader exists in Documents module
            doc_uploader = page.locator('[data-testid="stFileUploader"]').first
            expect(doc_uploader).to_be_visible()

            screenshot_path = tmp_path / "document_vision_tab.png"
            page.screenshot(path=str(screenshot_path))
            assert screenshot_path.exists()

            context.close()
            browser.close()

        videos = list(video_dir.glob("*.webm"))
        assert len(videos) > 0, "No Playwright video recorded"
    finally:
        proc.terminate()
        proc.wait(timeout=5)
