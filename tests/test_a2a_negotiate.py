import os
import pytest
import asyncio
from graph import a2a_negotiate, draft_po

@pytest.mark.skipif(not os.environ.get("META_API_KEY"), reason="META_API_KEY not set")
def test_a2a_negotiate_two_personas():
    state = {
        "tenant_id": "Tenant_A",
        "request_id": "test-req-123",
        "inventory_data": [
            {"sku": "SKU-404", "name": "Industrial Sensor", "quantity": 0, "location": "Warehouse-1"},
            {"sku": "SKU-200", "name": "Bolts", "quantity": 50, "location": "Warehouse-2"}
        ],
        "messages": [],
        "a2a_transcript": [],
        "drafted_plan": "",
        "status": "init",
        "pending_po": {}
    }

    result = asyncio.run(a2a_negotiate(state))

    transcript = result.get("a2a_transcript", [])
    assert len(transcript) == 2, f"Expected 2 turns (buyer and supplier), got {len(transcript)}"

    # First turn: Buyer Agent
    buyer_turn = transcript[0]
    assert buyer_turn.get("role") == "buyer_agent"
    assert "rfq" in buyer_turn or "response" in buyer_turn

    # Second turn: Supplier Agent
    supplier_turn = transcript[1]
    assert supplier_turn.get("role") == "supplier_agent"
    assert "response" in supplier_turn
    quote = supplier_turn["response"]
    assert isinstance(quote, dict)
    assert "restock_quantity" in quote
    assert "price_per_unit" in quote
    assert "lead_time_days" in quote

    # Check draft_po compatibility
    state["a2a_transcript"] = transcript
    po_res = draft_po(state)
    assert "pending_po" in po_res
    po = po_res["pending_po"]
    assert "restock_quantity" in po
    assert "price_per_unit" in po
    assert "lead_time_days" in po
