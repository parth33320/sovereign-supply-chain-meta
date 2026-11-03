import io
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


def test_app_shelf_image_uploader_exists():
    """Test that app.py sidebar contains file uploader for shelf image."""
    import streamlit.testing.v1 as st_test
    app_path = REPO_ROOT / "app.py"
    at = st_test.AppTest.from_file(str(app_path), default_timeout=10)
    at.run()
    assert len(at.sidebar.file_uploader) >= 1
    uploader = at.sidebar.file_uploader[0]
    assert uploader.label == "Upload Shelf Image"


def test_app_shelf_image_file_too_large():
    """Test that uploading a file > 1MB triggers an error."""
    import streamlit.testing.v1 as st_test
    app_path = REPO_ROOT / "app.py"
    at = st_test.AppTest.from_file(str(app_path), default_timeout=10)
    at.run()

    large_bytes = b"0" * 1_000_001
    at.sidebar.file_uploader[0].upload("big_shelf.jpg", large_bytes)
    try:
        at.run()
    except Exception:
        pass

    assert len(at.sidebar.error) > 0
    assert "File too large. Please upload under 1MB." in at.sidebar.error[0].value


def test_app_shelf_image_upload_and_context_injection():
    """Test shelf image upload analyzes image, stores shelf_context, and prepends to prompt."""
    import streamlit.testing.v1 as st_test
    fake_img = b"\x89PNG\r\n\x1a\n"

    mock_analysis = {
        "items": [{"item": "Bolts", "fill_level": 0.2, "status": "low"}],
        "summary": "Bolts at 20% fill level."
    }

    with patch("warehouse_vision.analyze_shelf_image", return_value=mock_analysis) as mock_analyze, \
         patch("worker.process_agent_task.delay") as mock_delay, \
         patch("celery.result.AsyncResult") as mock_async_result, \
         patch("guardrails.check_prompt_injection", return_value=True):

        mock_task = MagicMock()
        mock_task.id = "mock-task-vision-1"
        mock_delay.return_value = mock_task

        mock_async_task = MagicMock()
        mock_async_task.state = "PENDING"
        mock_async_result.return_value = mock_async_task

        app_path = REPO_ROOT / "app.py"
        at = st_test.AppTest.from_file(str(app_path), default_timeout=10)
        at.run()

        # Upload valid image using upload helper
        at.sidebar.file_uploader[0].upload("shelf.png", fake_img)
        at.run()

        mock_analyze.assert_called_once_with(fake_img)
        assert at.session_state["shelf_context"] == mock_analysis

        # Submit text prompt
        at.chat_input[0].set_value("Reallocate low stock items")
        try:
            at.run()
        except Exception:
            pass

        # Verify dispatched prompt has prefix
        expected_dispatched = "[VISUAL SHELF ANALYSIS: Bolts at 20% fill level.]\nReallocate low stock items"
        assert at.session_state.get("pending_prompt") == expected_dispatched
        mock_delay.assert_called_once()
        assert mock_delay.call_args[0][2] == expected_dispatched


def test_warehouse_vision_ui_e2e_playwright(tmp_path):
    """Playwright E2E verification of shelf image uploader in sidebar."""
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

            # Check sidebar contains Warehouse Vision header and file uploader
            sidebar = page.locator('[data-testid="stSidebar"]')
            expect(sidebar).to_be_visible()

            vision_header = sidebar.get_by_role("heading", name="Warehouse Vision")
            expect(vision_header).to_be_visible()

            uploader = sidebar.locator('[data-testid="stFileUploader"]')
            expect(uploader).to_be_visible()
            expect(uploader).to_contain_text("Upload Shelf Image")

            screenshot_path = tmp_path / "warehouse_vision_sidebar.png"
            page.screenshot(path=str(screenshot_path))
            assert screenshot_path.exists()

            context.close()
            browser.close()

        videos = list(video_dir.glob("*.webm"))
        assert len(videos) > 0, "No Playwright video recorded"
    finally:
        proc.terminate()
        proc.wait(timeout=5)
