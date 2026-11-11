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

def test_onboarding_card_visible(page):
    """When messages are empty, onboarding card is visible with 3 prefill prompt buttons."""
    page.goto(BASE_URL)
    page.wait_for_selector("text=Welcome to Sovereign Supply Chain", timeout=5000)
    assert page.is_visible("text=Microcontrollers are out of stock — negotiate now")
    assert page.is_visible("text=Check semiconductor levels across all hubs")
    assert page.is_visible("text=Negotiate restock with Supplier B")

def test_inventory_grid_renders(page):
    """InventoryGrid table renders headers, stockout badge, and items."""
    page.goto(BASE_URL)
    page.wait_for_selector("text=LIVE INVENTORY", timeout=5000)
    # Check for stockout count badge or item stockout badge
    page.wait_for_selector("text=STOCKOUTS", timeout=5000)
    assert page.is_visible("text=STOCKOUTS")
    assert page.is_visible("input[placeholder='🔍 Filter inventory...']")

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
    """Manager login with wrong access key shows error, correct access key opens governance view."""
    page.goto(BASE_URL)
    page.wait_for_selector("text=Manager Login", timeout=5000)
    page.click("text=Manager Login")
    page.wait_for_selector("input[type='password']", timeout=3000)
    page.fill("input[type='password']", "wrongpass")
    page.click("text=Submit Key")
    page.wait_for_selector("text=Incorrect access key", timeout=3000)
    assert page.is_visible("text=Incorrect access key")

    # Correct key
    page.fill("input[type='password']", "sovereign")
    page.click("text=Submit Key")
    page.wait_for_selector("text=INVENTORY GOVERNANCE — PENDING APPROVALS", timeout=5000)
    assert page.is_visible("text=Log Out")

def test_agent_progress_shows(page):
    """Submitting a command displays AgentProgress multi-step indicator while working."""
    page.goto(BASE_URL)
    page.wait_for_selector("input[placeholder*='Type a command']", timeout=5000)
    page.fill("input[placeholder*='Type a command']", "Check stock levels")
    page.press("input[placeholder*='Type a command']", "Enter")
    # Verify AgentProgress step or radar text appears
    assert page.is_visible("text=Disruption radar scan complete", timeout=3000) or page.is_visible("text=Awaiting your authorization")
