import os
import json
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage, HumanMessage

from demand_forecaster import get_trend_data, forecast_sku_stockouts
from graph import forecast_demand, get_graph, AgentState


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_sap.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE task_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            status TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    return str(db_file)


def test_get_trend_data_empty(temp_db):
    data = get_trend_data(temp_db)
    assert data == []


def test_get_trend_data_filters_30_days_and_fallback(temp_db):
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    # Insert older row (> 30 days)
    cursor.execute(
        "INSERT INTO task_queue (request_id, status, payload, created_at) VALUES (?, ?, ?, datetime('now', '-45 days'))",
        ("req_old", "EXECUTED", '{"plan": "Old plan for SKU_OLD"}')
    )
    conn.commit()
    conn.close()

    # With only >30-day rows, 30-day query returns 0 rows, so it falls back to all available rows
    data = get_trend_data(temp_db)
    assert len(data) == 1
    assert 'Old plan for SKU_OLD' in data[0]

    # Now insert a fresh row (< 30 days)
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO task_queue (request_id, status, payload, created_at) VALUES (?, ?, ?, datetime('now', '-5 days'))",
        ("req_new", "DRAFTED", '{"plan": "New plan for SKU_NEW"}')
    )
    conn.commit()
    conn.close()

    # Now that a row within 30 days exists, only the row within 30 days should be returned
    data2 = get_trend_data(temp_db)
    assert len(data2) == 1
    assert 'New plan for SKU_NEW' in data2[0]


@patch("demand_forecaster.ChatOpenAI")
def test_forecast_sku_stockouts_mocked_llm(mock_chat_openai_cls, temp_db):
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO task_queue (request_id, status, payload, created_at) VALUES (?, ?, ?, datetime('now', '-2 days'))",
        ("req_1", "EXECUTED", '{"plan": "Reallocated 500 units of SKU_A"}')
    )
    conn.commit()
    conn.close()

    mock_llm = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = '```json\n[{"sku": "SKU_A", "days_until_stockout": 3, "confidence": "high"}, {"sku": "SKU_B", "days_until_stockout": 6, "confidence": "low"}]\n```'
    mock_llm.invoke.return_value = mock_resp
    mock_chat_openai_cls.return_value = mock_llm

    forecasts = forecast_sku_stockouts(db_path=temp_db)
    assert len(forecasts) == 2
    assert forecasts[0] == {"sku": "SKU_A", "days_until_stockout": 3, "confidence": "high"}
    assert forecasts[1] == {"sku": "SKU_B", "days_until_stockout": 6, "confidence": "low"}

    mock_llm.invoke.assert_called_once()
    prompt_sent = mock_llm.invoke.call_args[0][0][0].content
    assert "Based on this reallocation history, which SKUs will stockout in the next 7 days? Return JSON: [{sku, days_until_stockout, confidence}]" in prompt_sent
    assert "Reallocated 500 units of SKU_A" in prompt_sent


@patch("demand_forecaster.ChatOpenAI")
def test_forecast_sku_stockouts_invalid_json(mock_chat_openai_cls, temp_db):
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO task_queue (request_id, status, payload) VALUES (?, ?, ?)",
        ("req_1", "EXECUTED", '{"plan": "Reallocation data"}')
    )
    conn.commit()
    conn.close()

    mock_llm = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = "Not valid JSON response"
    mock_llm.invoke.return_value = mock_resp
    mock_chat_openai_cls.return_value = mock_llm

    forecasts = forecast_sku_stockouts(db_path=temp_db)
    assert forecasts == []


@patch("graph.forecast_sku_stockouts")
def test_forecast_demand_node_alerts(mock_forecast_stockouts):
    mock_forecast_stockouts.return_value = [
        {"sku": "SKU-HIGH", "days_until_stockout": 2, "confidence": "high"},
        {"sku": "SKU-MED", "days_until_stockout": 5, "confidence": "medium"},
        {"sku": "SKU-LOW", "days_until_stockout": 7, "confidence": "low"},
    ]

    initial_messages = [HumanMessage(content="Check inventory")]
    state = {
        "messages": initial_messages,
        "tenant_id": "Tenant_A",
        "request_id": "req-123",
        "inventory_data": [],
        "drafted_plan": "",
        "status": "pending",
        "a2a_transcript": [],
        "pending_po": {}
    }

    result = forecast_demand(state)
    messages = result["messages"]

    # Only high confidence should produce an alert message
    assert len(messages) == 2
    assert messages[0] == initial_messages[0]
    assert isinstance(messages[1], AIMessage)
    assert messages[1].content == "[DEMAND FORECAST ALERT] (HIGH): SKU-HIGH predicted stockout in 2 days."


@patch("graph.forecast_sku_stockouts")
def test_forecast_demand_node_no_high_confidence(mock_forecast_stockouts):
    mock_forecast_stockouts.return_value = [
        {"sku": "SKU-MED", "days_until_stockout": 5, "confidence": "medium"},
        {"sku": "SKU-LOW", "days_until_stockout": 7, "confidence": "low"},
    ]

    state = {
        "messages": [HumanMessage(content="Check inventory")],
        "tenant_id": "Tenant_A",
        "request_id": "req-123",
        "inventory_data": [],
        "drafted_plan": "",
        "status": "pending",
        "a2a_transcript": [],
        "pending_po": {}
    }

    result = forecast_demand(state)
    assert len(result["messages"]) == 1  # No alert added


def test_graph_topology_forecast_demand():
    graph = get_graph()
    nodes = graph.nodes
    assert "forecast_demand" in nodes
    assert "global_oracle" in nodes
    assert "fetch_inventory" in nodes


def test_forecast_sku_stockouts_live_smoke():
    api_key = os.environ.get("META_API_KEY")
    if not api_key:
        pytest.skip("META_API_KEY not set; skipping live smoke test")

    results = forecast_sku_stockouts()
    assert isinstance(results, list)
    for item in results:
        assert "sku" in item
        assert "days_until_stockout" in item
        assert item["confidence"] in ["low", "medium", "high"]
