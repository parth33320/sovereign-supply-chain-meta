import os
import json
import pytest
from unittest.mock import MagicMock, patch
from warehouse_vision import analyze_shelf_image


def test_analyze_shelf_image_empty_bytes():
    with pytest.raises(ValueError, match="Invalid or empty image bytes"):
        analyze_shelf_image(b"")


def test_analyze_shelf_image_invalid_type():
    with pytest.raises(ValueError, match="Invalid or empty image bytes"):
        analyze_shelf_image(None)  # type: ignore


def test_analyze_shelf_image_sam_success():
    fake_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    expected_output = {
        "items": [
            {"item": "Industrial Bearings", "fill_level": 0.8, "status": "ok"},
            {"item": "Hydraulic Seals", "fill_level": 0.15, "status": "low"}
        ],
        "summary": "Industrial Bearings at 80% (ok), Hydraulic Seals at 15% (low)."
    }

    mock_llm_response = MagicMock()
    mock_llm_response.content = json.dumps(expected_output)

    with patch("warehouse_vision.ChatOpenAI") as mock_chat_cls:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = mock_llm_response
        mock_chat_cls.return_value = mock_instance

        result = analyze_shelf_image(fake_image)

        assert result == expected_output
        mock_chat_cls.assert_called_once()
        assert mock_chat_cls.call_args.kwargs["model"] == "sam-3.1"


def test_analyze_shelf_image_sam_fallback_to_muse_spark():
    fake_image = b"fake_image_bytes"
    expected_output = {
        "items": [
            {"item": "Pallet A", "fill_level": 0.0, "status": "empty"}
        ],
        "summary": "Pallet A is empty."
    }

    mock_sam_instance = MagicMock()
    mock_sam_instance.invoke.side_effect = Exception("404 Not Found: model sam-3.1 not found")

    mock_fallback_instance = MagicMock()
    mock_fallback_instance.invoke.return_value = MagicMock(content=json.dumps(expected_output))

    with patch("warehouse_vision.ChatOpenAI") as mock_chat_cls:
        # First call for sam-3.1 returns mock_sam_instance, second call for muse-spark-1.3 returns mock_fallback_instance
        mock_chat_cls.side_effect = [mock_sam_instance, mock_fallback_instance]

        result = analyze_shelf_image(fake_image)

        assert result == expected_output
        assert mock_chat_cls.call_count == 2
        first_call_model = mock_chat_cls.call_args_list[0].kwargs["model"]
        second_call_model = mock_chat_cls.call_args_list[1].kwargs["model"]
        assert first_call_model == "sam-3.1"
        assert second_call_model == "muse-spark-1.3"


def test_analyze_shelf_image_json_in_markdown():
    fake_image = b"fake_image_bytes"
    raw_markdown = """```json
{
  "items": [{"item": "Steel Bolts", "fill_level": 0.5, "status": "ok"}],
  "summary": "Steel Bolts at 50% capacity."
}
```"""
    mock_llm_response = MagicMock(content=raw_markdown)

    with patch("warehouse_vision.ChatOpenAI") as mock_chat_cls:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = mock_llm_response
        mock_chat_cls.return_value = mock_instance

        result = analyze_shelf_image(fake_image)
        assert len(result["items"]) == 1
        assert result["items"][0]["item"] == "Steel Bolts"
        assert result["items"][0]["fill_level"] == 0.5
        assert result["items"][0]["status"] == "ok"
        assert result["summary"] == "Steel Bolts at 50% capacity."


def test_analyze_shelf_image_malformed_json_fallback():
    fake_image = b"fake_image_bytes"
    mock_llm_response = MagicMock(content="I see some boxes on the shelf but cannot produce JSON.")

    with patch("warehouse_vision.ChatOpenAI") as mock_chat_cls:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = mock_llm_response
        mock_chat_cls.return_value = mock_instance

        result = analyze_shelf_image(fake_image)
        assert "items" in result
        assert "summary" in result
        assert isinstance(result["items"], list)
        assert len(result["items"]) == 0
        assert "I see some boxes" in result["summary"]


def test_analyze_shelf_image_live_smoke():
    api_key = os.environ.get("META_API_KEY")
    if not api_key:
        pytest.skip("META_API_KEY is not set, skipping live smoke test")

    # 1x1 transparent PNG bytes
    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
        b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    result = analyze_shelf_image(tiny_png)
    assert isinstance(result, dict)
    assert "items" in result
    assert "summary" in result
    assert isinstance(result["items"], list)
    assert isinstance(result["summary"], str)
