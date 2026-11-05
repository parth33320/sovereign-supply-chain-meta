import json
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from graph import get_graph, validate_inventory_items, extract_item_candidates, log_dpo
from warehouse_vision import analyze_shelf_image
from document_vision import extract_document_data


def test_extract_item_candidates():
    # Quoted items
    assert "Titanium Bolts" in extract_item_candidates("Please check 'Titanium Bolts' in stock")
    # Explicit item/SKU keywords
    assert "SKU-9921" in extract_item_candidates("Order sku SKU-9921 now")
    assert "Gadget X" in extract_item_candidates("Please reallocate item Gadget X to regional hub")
    # Hyphenated SKUs
    assert "SKU-STEEL-99" in extract_item_candidates("Ship SKU-STEEL-99 to east plant")


def test_graph_validation_blocks_unknown_item():
    graph = get_graph()
    state = {
        "messages": [HumanMessage(content="Please dispatch item Titanium Screws to factory")],
        "tenant_id": "Tenant_A",
        "request_id": "test-req-unknown",
        "status": "init"
    }
    result = graph.invoke(state)

    # Check status and unknown item
    assert result.get("status") == "item_not_found"
    assert result.get("unknown_item") == "Titanium Screws"

    # Must contain AIMessage with the exact required phrasing
    expected_msg = "Item 'Titanium Screws' not found in inventory. Please retry or request manager approval to add new item"
    ai_msgs = [m for m in result.get("messages", []) if isinstance(m, AIMessage)]
    assert any(m.content == expected_msg for m in ai_msgs)

    # Verify it stopped without generating a drafted plan or pending PO
    assert "drafted_plan" not in result or result["drafted_plan"] == ""
    assert "pending_po" not in result or result["pending_po"] is None


def test_graph_validation_allows_known_item():
    state = {
        "messages": [HumanMessage(content="Check level for item Semiconductors")],
        "inventory_data": [
            {"item_name": "Semiconductors", "quantity": 500, "tenant_id": "Tenant_A"},
            {"item_name": "Copper Wire", "quantity": 2000, "tenant_id": "Tenant_A"}
        ],
        "tenant_id": "Tenant_A",
        "request_id": "test-req-known",
        "status": "init"
    }
    validation_res = validate_inventory_items(state)
    assert validation_res.get("status") != "item_not_found"
    assert "unknown_item" not in validation_res


def test_warehouse_vision_blocks_unknown_item():
    fake_img = b"fake_shelf_bytes"
    with patch("warehouse_vision.ChatOpenAI") as mock_llm:
        mock_instance = MagicMock()
        mock_llm.return_value = mock_instance
        mock_instance.invoke.return_value.content = json.dumps({
            "items": [{"item": "Mystery Part 404", "fill_level": 0.5, "status": "ok"}],
            "summary": "Detected 1 item on shelf."
        })

        res = analyze_shelf_image(fake_img, tenant_id="Tenant_A")
        assert "error" in res
        assert res["error"] == "Item 'Mystery Part 404' not found in inventory. Upload rejected."
        assert res["unknown_item"] == "Mystery Part 404"
        assert res["items"] == []


def test_warehouse_vision_allows_known_item():
    fake_img = b"fake_shelf_bytes"
    with patch("warehouse_vision.ChatOpenAI") as mock_llm:
        mock_instance = MagicMock()
        mock_llm.return_value = mock_instance
        mock_instance.invoke.return_value.content = json.dumps({
            "items": [{"item": "Semiconductors", "fill_level": 0.9, "status": "ok"}],
            "summary": "Semiconductors in stock."
        })

        res = analyze_shelf_image(fake_img, tenant_id="Tenant_A")
        assert "error" not in res
        assert len(res.get("items", [])) == 1
        assert res["items"][0]["item"] == "Semiconductors"


def test_document_vision_blocks_unknown_item():
    fake_doc = b"fake_doc_bytes"
    with patch("document_vision.ChatOpenAI") as mock_llm:
        mock_instance = MagicMock()
        mock_llm.return_value = mock_instance
        mock_instance.invoke.return_value.content = json.dumps({
            "supplier": "Apex Global Parts",
            "dates": ["2026-11-05"],
            "items": [{"description": "Unregistered Widget X", "quantity": 100, "unit_price": 25.0}],
            "raw_summary": "Invoice for Unregistered Widget X"
        })

        res = extract_document_data(fake_doc, tenant_id="Tenant_A")
        assert "error" in res
        assert res["error"] == "SKU 'Unregistered Widget X' not found in inventory. Manager approval required to add new item."
        assert res["unknown_item"] == "Unregistered Widget X"
        assert res["items"] == []


def test_document_vision_allows_known_item():
    fake_doc = b"fake_doc_bytes"
    with patch("document_vision.ChatOpenAI") as mock_llm:
        mock_instance = MagicMock()
        mock_llm.return_value = mock_instance
        mock_instance.invoke.return_value.content = json.dumps({
            "supplier": "Apex Global Parts",
            "dates": ["2026-11-05"],
            "items": [{"description": "Copper Wire", "quantity": 500, "unit_price": 5.0}],
            "raw_summary": "Invoice for Copper Wire"
        })

        res = extract_document_data(fake_doc, tenant_id="Tenant_A")
        assert "error" not in res
        assert len(res.get("items", [])) == 1
        assert res["items"][0]["description"] == "Copper Wire"


def test_manager_approval_log_dpo(tmp_path):
    log_file = tmp_path / "dpo_test.json"
    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        log_dpo(
            prompt="Manager approval request to add new inventory item: Titanium Screws",
            chosen="APPROVED",
            rejected="REJECTED"
        )
        assert mock_file.write.called
        written_data = mock_file.write.call_args[0][0]
        parsed = json.loads(written_data)
        assert parsed["chosen"] == "APPROVED"
        assert "Titanium Screws" in parsed["prompt"]
