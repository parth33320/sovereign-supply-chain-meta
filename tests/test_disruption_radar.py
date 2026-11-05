import os
import json
import pytest
from unittest.mock import patch, MagicMock

# Attempt import of disruption_radar
try:
    from disruption_radar import fetch_disruption_alert, clear_disruption_cache
except ImportError:
    fetch_disruption_alert = None
    clear_disruption_cache = lambda: None

@pytest.fixture(autouse=True)
def reset_cache_between_tests():
    clear_disruption_cache()
    yield
    clear_disruption_cache()

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Supply Chain News</title>
    <item>
      <title>Major Port Strike Shuts Down East Coast Terminals</title>
      <description>Workers initiate strike causing massive cargo delays.</description>
    </item>
    <item>
      <title>Canal Drought Limits Vessel Transit Capacity</title>
      <description>Water levels drop significantly delaying container ships.</description>
    </item>
    <item>
      <title>Rail Network Facing Maintenance Disruptions</title>
      <description>Freight trains delayed by up to 48 hours across major corridors.</description>
    </item>
    <item>
      <title>Air Freight Volumes Rise Amid Ocean Congestion</title>
      <description>Shippers pivot to air cargo as sea routes face backlogs.</description>
    </item>
    <item>
      <title>Trucking Capacity Tightens in Midwest</title>
      <description>Reefer and dry van rates climb due to driver shortages.</description>
    </item>
    <item>
      <title>Sixth Story Headline Should Be Ignored</title>
      <description>Only top 5 headlines per feed should be sampled.</description>
    </item>
  </channel>
</rss>
"""

SAMPLE_BENIGN_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Normal News</title>
    <item>
      <title>Logistics Conference Announces 2025 Keynote Speaker</title>
      <description>Industry leaders gather to discuss standard technology trends.</description>
    </item>
  </channel>
</rss>
"""


def test_fetch_disruption_alert_import():
    assert fetch_disruption_alert is not None, "fetch_disruption_alert should be importable"


@patch("disruption_radar.requests.get")
@patch("disruption_radar.get_llm")
def test_fetch_disruption_alert_happy_path(mock_get_llm, mock_requests_get):
    # Mock RSS response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_RSS_XML
    mock_requests_get.return_value = mock_resp

    # Mock ChatOpenAI response
    mock_llm_instance = MagicMock()
    mock_ai_message = MagicMock()
    mock_ai_message.content = '```json\n{"alert": true, "severity": "high", "summary": "Port strike and canal drought causing severe supply chain delays."}\n```'
    mock_llm_instance.invoke.return_value = mock_ai_message
    mock_get_llm.return_value = mock_llm_instance

    result = fetch_disruption_alert()

    assert isinstance(result, dict)
    assert result == {
        "alert": True,
        "severity": "high",
        "summary": "Port strike and canal drought causing severe supply chain delays."
    }
    assert mock_requests_get.call_count == 2
    mock_llm_instance.invoke.assert_called_once()


@patch("disruption_radar.requests.get")
@patch("disruption_radar.get_llm")
def test_fetch_disruption_alert_no_disruptions(mock_get_llm, mock_requests_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_BENIGN_RSS_XML
    mock_requests_get.return_value = mock_resp

    mock_llm_instance = MagicMock()
    mock_ai_message = MagicMock()
    mock_ai_message.content = '{"alert": false, "severity": "low", "summary": "No active supply chain disruptions identified in recent news."}'
    mock_llm_instance.invoke.return_value = mock_ai_message
    mock_get_llm.return_value = mock_llm_instance

    result = fetch_disruption_alert()

    assert result["alert"] is False
    assert result["severity"] == "low"
    assert "No active supply chain disruptions" in result["summary"]


@patch("disruption_radar.requests.get")
def test_fetch_disruption_alert_network_failure(mock_requests_get):
    # Simulate network exception on fetch
    mock_requests_get.side_effect = Exception("Connection timed out")

    result = fetch_disruption_alert()

    assert result == {
        "alert": False,
        "severity": "low",
        "summary": "No disruption data available."
    }


@patch("disruption_radar.requests.get")
def test_fetch_disruption_alert_invalid_xml(mock_requests_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "NOT XML <>>"
    mock_requests_get.return_value = mock_resp

    result = fetch_disruption_alert()

    assert result == {
        "alert": False,
        "severity": "low",
        "summary": "No disruption data available."
    }


@patch("disruption_radar.requests.get")
@patch("disruption_radar.get_llm")
def test_fetch_disruption_alert_invalid_llm_json(mock_get_llm, mock_requests_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_RSS_XML
    mock_requests_get.return_value = mock_resp

    mock_llm_instance = MagicMock()
    mock_ai_message = MagicMock()
    mock_ai_message.content = "I cannot fulfill this in JSON format."
    mock_llm_instance.invoke.return_value = mock_ai_message
    mock_get_llm.return_value = mock_llm_instance

    result = fetch_disruption_alert()

    assert result == {
        "alert": False,
        "severity": "low",
        "summary": "No disruption data available."
    }


def test_fetch_disruption_alert_live_integration():
    api_key = os.environ.get("META_API_KEY")
    if not api_key:
        pytest.skip("META_API_KEY not set; skipping live integration test")

    result = fetch_disruption_alert()
    assert isinstance(result, dict)
    assert "alert" in result
    assert isinstance(result["alert"], bool)
    assert result["severity"] in ["low", "medium", "high"]
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 0
