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
    """Test that app.py contains file uploader for shelf image in Warehouse module."""
    import streamlit.testing.v1 as st_test
    app_path = REPO_ROOT / "app.py"
    at = st_test.AppTest.from_file(str(app_path), default_timeout=10)
    at.run()
    at.sidebar.radio[0].set_value("Warehouse")
    at.run()

    uploaders = [u for u in at.file_uploader if u.key == "shelf_image_uploader"]
    assert len(uploaders) == 1
    assert uploaders[0].label == "Upload Shelf Image"


def test_app_shelf_image_file_too_large():
    """Test that uploading a file > 1MB triggers an error."""
    import streamlit.testing.v1 as st_test
    app_path = REPO_ROOT / "app.py"
    at = st_test.AppTest.from_file(str(app_path), default_timeout=10)
    at.run()
    at.sidebar.radio[0].set_value("Warehouse")
    at.run()

    large_bytes = b"0" * 1_000_001
    shelf_uploader = [u for u in at.file_uploader if u.key == "shelf_image_uploader"][0]
    shelf_uploader.upload("big_shelf.jpg", large_bytes)
    try:
        at.run()
    except Exception:
        pass

    assert len(at.error) > 0
    assert any("File too large. Please upload under 1MB." in err.value for err in at.error)


def test_app_shelf_image_upload_and_context_injection():
    """Test shelf image upload analyzes image, stores shelf_context, and prepends to prompt."""
    import streamlit.testing.v1 as st_test
    fake_img = b"\x89PNG\r\n\x1a\n"

    mock_analysis = {
        "items": [{"item": "Bolts", "fill_level": 0.2, "status": "low"}],
        "summary": "Bolts at 20% fill level."
    }

    with patch("warehouse_vision.analyze_shelf_image", return_value=mock_analysis) as mock_analyze, \
         patch("graph.get_graph_with_postgres") as mock_get_graph, \
         patch("guardrails.check_prompt_injection", return_value=True):
        mock_graph = MagicMock()
        mock_get_graph.return_value = mock_graph
        mock_graph.invoke.return_value = {
            "messages": [],
            "drafted_plan": ""
        }

        app_path = REPO_ROOT / "app.py"
        at = st_test.AppTest.from_file(str(app_path), default_timeout=10)
        at.run()

        # Navigate to Warehouse
        at.sidebar.radio[0].set_value("Warehouse")
        at.run()

        # Upload valid image using upload helper
        shelf_uploader = [u for u in at.file_uploader if u.key == "shelf_image_uploader"][0]
        shelf_uploader.upload("shelf.png", fake_img)
        at.run()

        mock_analyze.assert_called_once_with(fake_img)
        assert at.session_state["shelf_context"] == mock_analysis

        # Switch back to Orchestrator to submit text prompt
        at.sidebar.radio[0].set_value("Orchestrator")
        at.run()

        at.chat_input[0].set_value("Reallocate low stock items")
        try:
            at.run()
        except Exception:
            pass

        # Verify dispatched prompt has prefix
        expected_dispatched = "[VISUAL SHELF ANALYSIS: Bolts at 20% fill level.]\nReallocate low stock items"
        assert at.session_state.get("pending_prompt") == expected_dispatched
        mock_graph.invoke.assert_called_once()
        state_arg = mock_graph.invoke.call_args[0][0]
        assert state_arg["messages"][0].content == expected_dispatched


def test_warehouse_vision_ui_e2e_playwright(tmp_path):
    """Playwright E2E verification of shelf image uploader in Warehouse module."""
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

            expect(page).to_have_title("Sovereign Supply Chain Orchestrator", timeout=15000)

            # Check sidebar contains navigation rail and click Warehouse
            sidebar = page.locator('[data-testid="stSidebar"]')
            expect(sidebar).to_be_visible()

            warehouse_nav = sidebar.locator('label', has_text="Warehouse")
            expect(warehouse_nav).to_be_visible()
            warehouse_nav.click()
            time.sleep(1)

            # Check file uploader in Warehouse module
            uploader = page.locator('[data-testid="stFileUploader"]').first
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
