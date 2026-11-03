import os
import pytest
from unittest.mock import patch
from langchain_core.messages import HumanMessage, AIMessage

from graph import global_oracle, AgentState


def test_global_oracle_calls_disruption_radar_alert_true():
    """
    Test that global_oracle calls disruption_radar and formats alert message as:
    [GLOBAL ORACLE ALERT] ({severity.upper()}): {summary}
    """
    state: AgentState = {
        "messages": [HumanMessage(content="Check inventory for electronics")],
        "tenant_id": "tenant-123",
        "request_id": "req-abc",
        "inventory_data": [],
        "drafted_plan": "",
        "status": "pending",
        "a2a_transcript": [],
        "pending_po": {}
    }

    mock_alert_data = {
        "alert": True,
        "severity": "high",
        "summary": "Port strike detected in Long Beach causing container vessel backlogs."
    }

    with patch("graph.fetch_disruption_alert", return_value=mock_alert_data) as mock_radar:
        result = global_oracle(state)
        mock_radar.assert_called_once()

    assert "messages" in result
    messages = result["messages"]
    assert len(messages) == 2
    assert isinstance(messages[1], AIMessage)
    expected_content = "[GLOBAL ORACLE ALERT] (HIGH): Port strike detected in Long Beach causing container vessel backlogs."
    assert messages[1].content == expected_content


def test_global_oracle_calls_disruption_radar_alert_false():
    """
    Test that global_oracle is silent when alert is False.
    """
    initial_msg = HumanMessage(content="Check inventory for electronics")
    state: AgentState = {
        "messages": [initial_msg],
        "tenant_id": "tenant-123",
        "request_id": "req-abc",
        "inventory_data": [],
        "drafted_plan": "",
        "status": "pending",
        "a2a_transcript": [],
        "pending_po": {}
    }

    mock_alert_data = {
        "alert": False,
        "severity": "low",
        "summary": "No active supply chain disruptions detected."
    }

    with patch("graph.fetch_disruption_alert", return_value=mock_alert_data) as mock_radar:
        result = global_oracle(state)
        mock_radar.assert_called_once()

    assert "messages" in result
    messages = result["messages"]
    assert len(messages) == 1
    assert messages[0] == initial_msg


def test_global_oracle_live_integration():
    """
    Integration test: calls global_oracle() with real network/Meta LLM if META_API_KEY is present.
    Asserts messages list either unchanged (no alert) or contains GLOBAL ORACLE ALERT string.
    Skip if META_API_KEY unset.
    """
    if not os.environ.get("META_API_KEY"):
        pytest.skip("META_API_KEY unset; skipping live global_oracle integration test")

    initial_msg = HumanMessage(content="Evaluate real disruption radar integration")
    state: AgentState = {
        "messages": [initial_msg],
        "tenant_id": "tenant-live",
        "request_id": "req-live-1",
        "inventory_data": [],
        "drafted_plan": "",
        "status": "pending",
        "a2a_transcript": [],
        "pending_po": {}
    }

    result = global_oracle(state)
    assert "messages" in result
    messages = result["messages"]

    # Either no alert was added (silent) or an alert was added with the expected header
    if len(messages) == 1:
        assert messages[0] == initial_msg
    elif len(messages) == 2:
        assert isinstance(messages[1], AIMessage)
        assert "[GLOBAL ORACLE ALERT]" in messages[1].content
    else:
        pytest.fail(f"Unexpected messages count in global_oracle output: {len(messages)}")
