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
    """Test that app.py contains unified file uploader triggered via 📎."""
    import streamlit.testing.v1 as st_test
    app_path = REPO_ROOT / "app.py"
    at = st_test.AppTest.from_file(str(app_path), default_timeout=10)
    at.run()
    clip_btn = [b for b in at.button if b.key == "btn_file_trigger"][0]
    clip_btn.click().run()

    uploaders = [u for u in at.file_uploader if u.key == "unified_file_uploader"]
    assert len(uploaders) == 1
    assert "Logistics" in uploaders[0].label or "File" in uploaders[0].label

def test_app_shelf_image_file_too_large():
    """Test that uploading a file > 2MB triggers user error card."""
    import streamlit.testing.v1 as st_test
    app_path = REPO_ROOT / "app.py"
    at = st_test.AppTest.from_file(str(app_path), default_timeout=10)
    at.run()
    clip_btn = [b for b in at.button if b.key == "btn_file_trigger"][0]
    clip_btn.click().run()

    large_bytes = b"0" * 2_000_001
    uploader = [u for u in at.file_uploader if u.key == "unified_file_uploader"][0]
    uploader.upload("big_shelf.jpg", large_bytes)
    try:
        at.run()
    except Exception:
        pass

    has_err = any("exceeds 2MB" in m.value or "user-error-card" in m.value for m in at.markdown)
    assert has_err, "Expected user error card when uploading file > 2MB"

def test_warehouse_vision_ui_e2e_playwright(tmp_path):
    """Playwright E2E verification of unified file uploader trigger."""
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

            expect(page).to_have_title("Sovereign Supply Chain", timeout=15000)

            # Click 📎 button in input bar to open file drawer
            clip_btn = page.locator('button:has-text("📎")')
            expect(clip_btn).to_be_visible()
            clip_btn.click()

            # Verify unified file uploader appears
            uploader = page.locator('[data-testid="stFileUploader"]').first
            expect(uploader).to_be_visible()

            screenshot_path = tmp_path / "warehouse_vision_unified.png"
            page.screenshot(path=str(screenshot_path))
            assert screenshot_path.exists()

            context.close()
            browser.close()

        videos = list(video_dir.glob("*.webm"))
        assert len(videos) > 0, "No Playwright video recorded"
    finally:
        proc.terminate()
        proc.wait(timeout=5)
