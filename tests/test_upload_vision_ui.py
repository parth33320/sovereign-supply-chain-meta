"""UI verification test for file uploads, in-chat spinner, and chat bubbles."""

import os
import socket
import subprocess
import time
import pytest
from playwright.sync_api import sync_playwright

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

SERVER_PORT = find_free_port()
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"

@pytest.fixture(scope="module", autouse=True)
def run_app_server():
    subprocess.run(["npm", "run", "build"], cwd="frontend", check=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["DEMO_MODE"] = "1"
    proc = subprocess.Popen(
        ["uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(SERVER_PORT)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for _ in range(40):
        try:
            import urllib.request
            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=1) as resp:
                if resp.status == 200:
                    break
        except Exception:
            time.sleep(0.3)
    yield
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

@pytest.fixture
def page():
    os.makedirs("test-results/videos", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="test-results/videos",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        yield page
        context.close()
        browser.close()

def test_shelf_upload_displays_in_chat(page, tmp_path):
    page.goto(BASE_URL)
    page.wait_for_selector("input[placeholder*='Type a command']", timeout=5000)

    # Click paperclip to show file input
    page.click("button[aria-label='Attach file']")
    file_input = page.locator("input[type='file']")

    # Create sample shelf image
    test_shelf_img = tmp_path / "sample-shelf.png"
    test_shelf_img.write_bytes(b"\x89PNG\r\n\x1a\nfakeimage")

    # Upload file
    file_input.set_input_files(str(test_shelf_img))

    # Verify user message appears in chat
    page.wait_for_selector("text=📎 sample-shelf.png", timeout=5000)

    # Verify assistant message displays warehouse vision results
    page.wait_for_selector("text=Warehouse Shelf Analysis (Meta SAM 3.1)", timeout=10000)
    assert page.is_visible("text=Widget-A")

def test_invoice_upload_displays_in_chat(page, tmp_path):
    page.goto(BASE_URL)
    page.wait_for_selector("input[placeholder*='Type a command']", timeout=5000)

    page.click("button[aria-label='Attach file']")
    file_input = page.locator("input[type='file']")

    test_invoice_img = tmp_path / "invoice.png"
    test_invoice_img.write_bytes(b"\x89PNG\r\n\x1a\nfakeimage")

    file_input.set_input_files(str(test_invoice_img))

    page.wait_for_selector("text=📎 invoice.png", timeout=5000)
    page.wait_for_selector("text=Document Extraction (Meta Muse Image 1.0)", timeout=10000)
    assert page.is_visible("text=FastFreight Logistics")

def test_voice_wav_upload_triggers_transcription_and_chat(page, tmp_path):
    page.goto(BASE_URL)
    page.wait_for_selector("input[placeholder*='Type a command']", timeout=5000)

    page.click("button[aria-label='Attach file']")
    file_input = page.locator("input[type='file']")

    test_voice_file = tmp_path / "sample-voice.wav"
    test_voice_file.write_bytes(b"RIFF....WAVEfmt ....")

    file_input.set_input_files(str(test_voice_file))

    page.wait_for_selector("text=📎 sample-voice.wav", timeout=5000)
    page.wait_for_selector("text=🎙️ Transcribed:", timeout=10000)
    assert page.is_visible("text=Emergency restock Widget-A")
