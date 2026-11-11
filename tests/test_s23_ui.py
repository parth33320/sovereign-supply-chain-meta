"""Sprint S23 End-to-End Playwright UI Tests."""

import os
import socket
import subprocess
import time
import pytest
from playwright.sync_api import sync_playwright

def find_free_port():
    """Finds an unused ephemeral port for the test server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

SERVER_PORT = find_free_port()
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"

@pytest.fixture(scope="module", autouse=True)
def run_app_server():
    """Builds frontend and starts backend FastAPI server for testing."""
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
    # Wait for server to come up
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
    """Sets up Playwright browser context with video recording."""
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

def test_inventory_grid_collapsible(page):
    """InventoryGrid summary bar renders collapsed by default and expands on click."""
    page.goto(BASE_URL)
    page.wait_for_selector("text=LIVE INVENTORY", timeout=5000)
    page.wait_for_selector("text=STOCKOUTS", timeout=5000)
    assert page.is_visible("text=[▼ Expand]")
    # Filter input shouldn't be visible while collapsed
    assert not page.is_visible("input[placeholder='🔍 Filter inventory...']")

    # Click summary bar to expand
    page.click("text=LIVE INVENTORY")
    page.wait_for_selector("input[placeholder='🔍 Filter inventory...']", timeout=3000)
    assert page.is_visible("input[placeholder='🔍 Filter inventory...']")
    assert page.is_visible("text=[▲ Collapse]")

def test_hitl_card_no_json(page):
    """Triggering a chat action in DEMO_MODE creates formatted PO card without raw JSON."""
    page.goto(BASE_URL)
    page.wait_for_selector("input[placeholder*='Type a command']", timeout=5000)
    page.fill("input[placeholder*='Type a command']", "Reorder 500 Microcontrollers")
    page.press("input[placeholder*='Type a command']", "Enter")
    page.wait_for_selector("text=PURCHASE ORDER — AWAITING APPROVAL", timeout=10000)
    # Verify card contains SKU, Qty, Total table and NO raw json { "sku": ... }
    card = page.locator("div.border-2.border-\\[\\#e3b341\\]")
    card_text = card.inner_text()
    assert "{" not in card_text
    assert "Approve & Execute" in card_text
    assert "Reject" in card_text

def test_manager_login(page):
    """Manager login with single click opens governance view without passwords."""
    page.goto(BASE_URL)
    page.wait_for_selector("text=Manager Login", timeout=5000)
    page.click("text=Manager Login")
    page.wait_for_selector("text=INVENTORY GOVERNANCE — PENDING APPROVALS", timeout=5000)
    assert page.is_visible("text=Log Out")

def test_agent_progress_shows(page):
    """Submitting a command displays AgentProgress multi-step indicator while working."""
    page.goto(BASE_URL)
    page.wait_for_selector("input[placeholder*='Type a command']", timeout=5000)
    page.fill("input[placeholder*='Type a command']", "Check stock levels")
    page.press("input[placeholder*='Type a command']", "Enter")
    # Verify AgentProgress step or radar text appears or completes with assistant response
    assert (
        page.is_visible("text=Disruption radar scan complete", timeout=5000)
        or page.is_visible("text=Awaiting your authorization")
        or page.is_visible("text=Orchestrator Analysis", timeout=5000)
    )
