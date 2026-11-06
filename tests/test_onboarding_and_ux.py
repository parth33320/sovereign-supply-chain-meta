import os
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_onboarding_empty_states():
    os.environ["DEMO_MODE"] = "1"
    app_file = str(REPO_ROOT / "app.py")
    at = AppTest.from_file(app_file, default_timeout=15)
    at.run()
    assert not at.exception

    # Check Orchestrator starter buttons
    starter_labels = [b.label for b in at.button]
    assert "🚨 Emergency restock Widget-A" in starter_labels
    assert "📦 Check semiconductor inventory levels" in starter_labels
    assert "🔄 Rebalance stock from Warehouse A to B" in starter_labels

    # Click a starter button
    starter_btn = [b for b in at.button if b.label == "🚨 Emergency restock Widget-A"][0]
    starter_btn.click().run()
    assert at.session_state.prefilled_prompt == "🚨 Emergency restock Widget-A"

    # Switch to Warehouse module
    at.sidebar.radio[0].set_value("Warehouse").run()
    assert not at.exception
    warehouse_btns = [b.label for b in at.button]
    assert "Use sample image" in warehouse_btns

    # Switch to Documents module
    at.sidebar.radio[0].set_value("Documents").run()
    assert not at.exception
    doc_btns = [b.label for b in at.button]
    assert "Use sample invoice" in doc_btns

def test_clear_conversation():
    os.environ["DEMO_MODE"] = "1"
    app_file = str(REPO_ROOT / "app.py")
    at = AppTest.from_file(app_file, default_timeout=15)
    at.run()
    # Populate chat history
    at.session_state.chat_history = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi", "attribution": "test"}]
    at.run()
    clear_btns = [b for b in at.button if b.key == "clear_chat_btn"]
    assert len(clear_btns) == 1
    clear_btns[0].click().run()
    assert at.session_state.chat_history == []

def test_hitl_panel_controls():
    os.environ["DEMO_MODE"] = "1"
    app_file = str(REPO_ROOT / "app.py")
    at = AppTest.from_file(app_file, default_timeout=15)
    at.session_state.demo_paused_for_hitl = True
    at.session_state.demo_pending_po = {"po_id": "PO-123", "supplier": "Apex", "quantity": 10, "price_per_unit": 5}
    at.run()
    assert at.session_state.hitl_paused_at is not None

    approve_btns = [b for b in at.button if b.key == "hitl_approve_btn"]
    assert len(approve_btns) == 1
