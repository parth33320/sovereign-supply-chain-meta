import os
import pytest
from langchain_core.messages import AIMessage, HumanMessage

import portfolio
from portfolio import (
    calculate_wsjf,
    create_initiative,
    add_work_item,
    get_wsjf_ranked_backlog,
    record_agent_action,
    get_evms_snapshot,
    Initiative,
    WorkItem,
    init_portfolio_db,
)
from graph import execute_plan

def setup_function():
    # Reset / initialize clean db for tests
    conn = portfolio.get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM agent_actions")
    c.execute("DELETE FROM work_items")
    c.execute("DELETE FROM initiatives")
    conn.commit()
    conn.close()
    init_portfolio_db()

def test_wsjf_calculation():
    # Formula: (business_value + time_criticality + risk) / job_size
    # (8 + 7 + 3) / 2 = 18 / 2 = 9.0
    assert calculate_wsjf(8, 7, 3, 2) == 9.0

def test_evms_snapshot():
    # Seed DB with an initiative and work items
    init_id = "TEST-INIT"
    create_initiative("Cost Optimization", 50000.0, "2024-12-31", initiative_id=init_id)
    # Add work items
    w1 = add_work_item(init_id, "Item 1", 8, 7, 3, 2, story_points=5, status="done")
    record_agent_action(w1.id, "Executed automated supplier renegotiation", 5000.0)
    w2 = add_work_item(init_id, "Item 2", 5, 5, 2, 3, story_points=3, status="backlog")

    snapshot = get_evms_snapshot(init_id)
    assert snapshot["planned_value"] > 0
    assert snapshot["earned_value"] > 0
    assert snapshot["actual_cost"] > 0
    assert snapshot["spi"] > 0
    assert snapshot["cpi"] > 0

def test_wsjf_ranking():
    init_id = "RANK-INIT"
    create_initiative("Ranking Initiative", 10000.0, "2025-01-01", initiative_id=init_id)
    # item 1: wsjf = (9 + 9 + 7) / 2 = 12.5
    w1 = add_work_item(init_id, "High priority", 9, 9, 7, 2)
    # item 2: wsjf = (5 + 5 + 2) / 2 = 6.0
    w2 = add_work_item(init_id, "Low priority", 5, 5, 2, 2)

    backlog = get_wsjf_ranked_backlog(init_id)
    assert len(backlog) >= 2
    assert backlog[0].wsjf_score >= backlog[1].wsjf_score
    assert backlog[0].id == w1.id

def test_record_action():
    init_id = "ACTION-INIT"
    create_initiative("Action Initiative", 20000.0, "2025-06-30", initiative_id=init_id)
    w = add_work_item(init_id, "Negotiate Freight Rates", 8, 8, 4, 2, story_points=4, status="in_progress")

    initial_saving = w.actual_saving_usd
    record_agent_action(w.id, "Carrier rate renegotiated for Route A", 3500.0)

    backlog = get_wsjf_ranked_backlog(init_id)
    updated_item = next(item for item in backlog if item.id == w.id)
    assert updated_item.actual_saving_usd == initial_saving + 3500.0
    assert len(updated_item.agent_actions) > 0
    assert any("Carrier rate renegotiated" in action for action in updated_item.agent_actions)

def test_execute_plan_records_portfolio_action():
    init_id = "GRAPH-INIT"
    create_initiative("Graph Execution", 30000.0, "2025-05-01", initiative_id=init_id)
    w = add_work_item(init_id, "Execute PO Restock", 9, 8, 5, 2)

    state = {
        "tenant_id": "Tenant_A",
        "request_id": "REQ-12345",
        "messages": [HumanMessage(content="Optimize route"), AIMessage(content="Reallocated stock successfully, saving $2,450.00")],
        "work_item_id": w.id,
        "last_saving": "$2,450.00",
        "status": "approved"
    }

    result = execute_plan(state)
    assert result["status"] == "executed"

    backlog = get_wsjf_ranked_backlog(init_id)
    updated_w = next(item for item in backlog if item.id == w.id)
    assert updated_w.actual_saving_usd == 2450.0
    assert len(updated_w.agent_actions) == 1
