import os
import uuid
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from graph import builder, get_graph_with_postgres
from init_db import init_db

@pytest.fixture(autouse=True)
def setup_database():
    """Ensure clean baseline database before running e2e test."""
    init_db()


def test_e2e_full_scenario_decision_loop():
    """
    Scenario: Full supply chain decision loop for Tenant_A
    Step 1: Submit "Rebalance semiconductors from Warehouse A to B" via graph directly (bypass Celery for test)
    Step 2: Assert global_oracle ran — messages contain either no alert (silent) or "[GLOBAL ORACLE ALERT]"
    Step 3: Assert inventory fetched — inventory_data contains Tenant_A items
    Step 4: Assert graph paused at human_review — graph.get_state(config).next == ('human_review',)
    Step 5: Approve — graph.update_state(config, {"status": "approved"}), stream to completion
    Step 6: Assert task_queue has an EXECUTED record for this request_id
    Step 7: Assert drafted_plan is non-empty string
    """
    has_meta_key = bool(os.environ.get("META_API_KEY"))
    has_postgres = bool(os.environ.get("POSTGRES_DB_URI"))

    request_id = str(uuid.uuid4())
    tenant_id = "Tenant_A"
    thread_id = f"{tenant_id}_{request_id}"
    config = {"configurable": {"thread_id": thread_id}}

    if has_postgres:
        graph = get_graph_with_postgres()
    else:
        # Use MemorySaver fallback if Postgres is not configured in sandbox
        from langgraph.checkpoint.memory import MemorySaver
        graph = builder.compile(checkpointer=MemorySaver(), interrupt_before=["human_review"])

    # Prepare input state
    user_prompt = "Rebalance semiconductors from Warehouse A to B"
    initial_state = {
        "messages": [HumanMessage(content=user_prompt)],
        "tenant_id": tenant_id,
        "request_id": request_id,
        "status": "init"
    }

    def run_scenario():
        # Step 1: Submit via graph directly
        for _ in graph.stream(initial_state, config):
            pass

        paused_state = graph.get_state(config)

        # Step 2: Assert global_oracle ran
        messages = paused_state.values.get("messages", [])
        has_oracle_alert = any("[GLOBAL ORACLE ALERT]" in getattr(m, "content", "") for m in messages)
        # Oracle node ran and either added an alert or silently continued
        assert isinstance(messages, list) and len(messages) >= 2

        # Step 3: Assert inventory fetched — contains Tenant_A items
        inventory_data = paused_state.values.get("inventory_data", [])
        assert len(inventory_data) > 0, "Inventory data should not be empty"
        assert all(item.get("tenant_id") == "Tenant_A" for item in inventory_data)
        assert any(item.get("item_name") == "Semiconductors" for item in inventory_data)

        # Step 4: Assert graph paused at human_review
        assert paused_state.next == ("human_review",), f"Expected paused at human_review, got {paused_state.next}"

        # Step 5: Approve — update state and stream to completion
        graph.update_state(config, {"status": "approved"})
        for _ in graph.stream(None, config):
            pass

        completed_state = graph.get_state(config)

        # Step 6: Assert task_queue has an EXECUTED record for this request_id
        conn = sqlite3.connect("mock_sap.db")
        cursor = conn.cursor()
        cursor.execute("SELECT status, payload FROM task_queue WHERE request_id = ? AND status = 'EXECUTED'", (request_id,))
        records = cursor.fetchall()
        conn.close()
        assert len(records) > 0, f"Expected EXECUTED record in task_queue for request_id {request_id}"

        # Step 7: Assert drafted_plan is non-empty string
        drafted_plan = completed_state.values.get("drafted_plan", "")
        assert isinstance(drafted_plan, str) and len(drafted_plan.strip()) > 0
        assert "Plan:" in drafted_plan

    if not has_meta_key:
        mock_ai_content = MagicMock()
        mock_ai_content.content = "Reallocate 200 units of semiconductors from Warehouse A to Warehouse B"
        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = mock_ai_content
            mock_chat.return_value = mock_instance
            run_scenario()
    else:
        run_scenario()
