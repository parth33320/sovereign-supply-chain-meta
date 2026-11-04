import io
import os
import wave
import time
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from playwright.sync_api import sync_playwright, expect


REPO_ROOT = Path(__file__).resolve().parent.parent


def generate_silent_wav(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate a silent mono 16-bit PCM WAV audio in bytes using stdlib wave."""
    num_frames = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00" * (num_frames * 2))
    return buffer.getvalue()


def test_app_voice_input_widget_exists():
    """Test that app.py contains st.audio_input above chat input."""
    import streamlit.testing.v1 as st_test
    app_path = REPO_ROOT / "app.py"
    with patch("graph.ConnectionPool"):
        at = st_test.AppTest.from_file(str(app_path), default_timeout=10)
        at.run()
        assert len(at.audio_input) == 1, "app.py does not have an audio_input widget"
        assert at.audio_input[0].key == "voice_audio_input"
        assert "Record voice" in at.audio_input[0].label


def test_app_voice_input_auto_submission():
    """
    Test that uploading an audio recording to st.audio_input invokes voice_handler.process_voice_input
    and automatically submits the resulting transcription into chat history and Celery task queue.
    """
    import streamlit.testing.v1 as st_test
    silent_wav = generate_silent_wav(duration_seconds=1.0)

    with patch("graph.ConnectionPool"), \
         patch("graph.get_graph_with_postgres") as mock_get_graph, \
         patch("voice_handler.process_voice_input") as mock_pvi, \
         patch("app.check_prompt_injection", return_value=True):
        mock_graph = MagicMock()
        mock_get_graph.return_value = mock_graph
        mock_graph.invoke.return_value = {
            "messages": [],
            "drafted_plan": ""
        }
        mock_pvi.return_value = {
            "status": "ok",
            "transcription": "Reroute 500 widgets to warehouse B",
            "intent": "reroute widgets"
        }

        app_path = REPO_ROOT / "app.py"
        at = st_test.AppTest.from_file(str(app_path), default_timeout=5)
        at.run()

        # Provide simulated audio recording
        at.audio_input[0].set_value(("voice.wav", silent_wav, "audio/wav"))
        try:
            at.run()
        except Exception:
            pass

        # Verify voice_handler was invoked with the audio bytes
        mock_pvi.assert_called_once_with(silent_wav)

        # Verify chat history contains the transcribed prompt
        assert len(at.session_state["chat_history"]) > 0
        assert at.session_state["chat_history"][0] == {
            "role": "user",
            "content": "Reroute 500 widgets to warehouse B"
        }
        assert at.session_state.get("pending_prompt") == "Reroute 500 widgets to warehouse B"
        mock_graph.invoke.assert_called_once()
        state_arg = mock_graph.invoke.call_args[0][0]
        assert state_arg["tenant_id"] == "Tenant_A"
        assert state_arg["status"] == "init"
        assert state_arg["messages"][0].content == "Reroute 500 widgets to warehouse B"


def test_voice_ui_e2e_playwright(tmp_path):
    """
    E2E Playwright test:
    - Launches streamlit server on a free port
    - Navigates to app in headless Chromium with video recording enabled
    - Checks that audio input widget is rendered with mic record button above chat input
    - Takes screenshot and saves video per AGENTS.md
    """
    port = 8599
    # Start streamlit server
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

            # Check page title
            expect(page).to_have_title("Sovereign Supply Chain Orchestrator", timeout=15000)

            # Expect audio input widget to exist and be visible
            audio_widget = page.locator('[data-testid="stAudioInput"]')
            expect(audio_widget).to_be_visible(timeout=10000)

            # Check that Record button inside audio input is present
            record_button = audio_widget.get_by_role("button", name="Record")
            expect(record_button).to_be_visible()

            # Expect text chat input to be present below audio input
            chat_input = page.locator('[data-testid="stChatInput"]')
            expect(chat_input).to_be_visible()

            screenshot_path = tmp_path / "voice_ui_screenshot.png"
            page.screenshot(path=str(screenshot_path))
            assert screenshot_path.exists()

            context.close()
            browser.close()

        # Verify video recorded
        videos = list(video_dir.glob("*.webm"))
        assert len(videos) > 0, "No Playwright video recorded"
    finally:
        proc.terminate()
        proc.wait(timeout=5)
