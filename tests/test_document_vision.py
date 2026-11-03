import os
import json
import pytest
from unittest.mock import MagicMock, patch
from document_vision import extract_document_data, format_logistics_instruction


def test_extract_document_data_empty_bytes():
    with pytest.raises(ValueError, match="Invalid or empty image bytes"):
        extract_document_data(b"")


def test_extract_document_data_invalid_type():
    with pytest.raises(ValueError, match="Invalid or empty image bytes"):
        extract_document_data(None)  # type: ignore


def test_extract_document_data_muse_image_success():
    fake_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    expected_output = {
        "supplier": "Acme Industrial Supplies",
        "dates": ["2025-05-10", "2025-05-15"],
        "items": [
            {"description": "Industrial Bearings", "quantity": 100, "unit_price": 12.50},
            {"description": "Hydraulic Seals", "quantity": 50, "unit_price": 5.00}
        ],
        "raw_summary": "Invoice from Acme Industrial Supplies for bearings and seals."
    }

    mock_llm_response = MagicMock()
    mock_llm_response.content = json.dumps(expected_output)

    with patch("document_vision.ChatOpenAI") as mock_chat_cls:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = mock_llm_response
        mock_chat_cls.return_value = mock_instance

        result = extract_document_data(fake_image)

        assert result["supplier"] == "Acme Industrial Supplies"
        assert result["dates"] == ["2025-05-10", "2025-05-15"]
        assert len(result["items"]) == 2
        assert result["items"][0]["description"] == "Industrial Bearings"
        assert result["items"][0]["quantity"] == 100
        mock_chat_cls.assert_called_once()
        assert mock_chat_cls.call_args.kwargs["model"] == "muse-image-1.0"


def test_extract_document_data_muse_image_fallback_to_muse_spark():
    fake_image = b"fake_invoice_bytes"
    expected_output = {
        "supplier": "Global Fasteners Corp",
        "dates": ["2025-06-01"],
        "items": [
            {"description": "Hex Bolts M8", "quantity": 500, "unit_price": 0.25}
        ],
        "raw_summary": "Invoice from Global Fasteners Corp."
    }

    mock_muse_image_instance = MagicMock()
    mock_muse_image_instance.invoke.side_effect = Exception("404 Not Found: model muse-image-1.0 not found")

    mock_fallback_instance = MagicMock()
    mock_fallback_instance.invoke.return_value = MagicMock(content=json.dumps(expected_output))

    with patch("document_vision.ChatOpenAI") as mock_chat_cls:
        mock_chat_cls.side_effect = [mock_muse_image_instance, mock_fallback_instance]

        result = extract_document_data(fake_image)

        assert result["supplier"] == "Global Fasteners Corp"
        assert result["items"][0]["quantity"] == 500
        assert mock_chat_cls.call_count == 2
        assert mock_chat_cls.call_args_list[0].kwargs["model"] == "muse-image-1.0"
        assert mock_chat_cls.call_args_list[1].kwargs["model"] == "muse-spark-1.3"


def test_extract_document_data_markdown_code_block():
    fake_image = b"fake_image_bytes"
    raw_markdown = """```json
{
  "supplier": "Apex Logistics",
  "dates": ["2025-04-20"],
  "items": [{"description": "Filter Cartridges", "quantity": 20, "unit_price": 45.0}],
  "raw_summary": "Shipping document from Apex Logistics"
}
```"""
    mock_llm_response = MagicMock(content=raw_markdown)

    with patch("document_vision.ChatOpenAI") as mock_chat_cls:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = mock_llm_response
        mock_chat_cls.return_value = mock_instance

        result = extract_document_data(fake_image)
        assert result["supplier"] == "Apex Logistics"
        assert result["dates"] == ["2025-04-20"]
        assert len(result["items"]) == 1
        assert result["items"][0]["description"] == "Filter Cartridges"
        assert result["items"][0]["quantity"] == 20


def test_extract_document_data_malformed_json_fallback():
    fake_image = b"fake_image_bytes"
    mock_llm_response = MagicMock(content="Non-JSON text: Received invoice from Supplier X.")

    with patch("document_vision.ChatOpenAI") as mock_chat_cls:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = mock_llm_response
        mock_chat_cls.return_value = mock_instance

        result = extract_document_data(fake_image)
        assert result["supplier"] == ""
        assert result["items"] == []
        assert result["dates"] == []
        assert "Non-JSON text" in result["raw_summary"]


def test_format_logistics_instruction():
    extracted = {
        "supplier": "Acme Industrial Supplies",
        "dates": ["2025-05-10"],
        "items": [
            {"description": "Industrial Bearings", "quantity": 100},
            {"description": "Hydraulic Seals", "quantity": 50}
        ],
        "raw_summary": "Invoice"
    }
    instruction = format_logistics_instruction(extracted)
    assert "Acme Industrial Supplies" in instruction
    assert "100x Industrial Bearings" in instruction
    assert "50x Hydraulic Seals" in instruction
    assert "2025-05-10" in instruction

    # Test empty fields fallback
    empty_extracted = {
        "supplier": "",
        "dates": [],
        "items": [],
        "raw_summary": "Brief receipt"
    }
    fallback_instruction = format_logistics_instruction(empty_extracted)
    assert "Process incoming shipment" in fallback_instruction


def test_extract_document_data_live_smoke():
    api_key = os.environ.get("META_API_KEY")
    if not api_key:
        pytest.skip("META_API_KEY is not set, skipping live smoke test")

    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
        b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    result = extract_document_data(tiny_png)
    assert isinstance(result, dict)
    assert "supplier" in result
    assert "dates" in result
    assert "items" in result
    assert "raw_summary" in result
    assert isinstance(result["items"], list)
