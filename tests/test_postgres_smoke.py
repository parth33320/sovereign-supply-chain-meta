import os
import uuid
import pytest
from graph import get_graph_with_postgres

def test_postgres_checkpointer_smoke():
    db_uri = os.environ.get("POSTGRES_DB_URI")
    if not db_uri:
        pytest.skip("POSTGRES_DB_URI not set")

    graph = get_graph_with_postgres()
    thread_id = f"smoke_test_{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    dummy_state = {
        "messages": [],
        "tenant_id": "Tenant_A",
        "request_id": str(uuid.uuid4()),
        "status": "init",
        "inventory_data": [{"item_name": "Test_Widget", "quantity": 10}],
        "drafted_plan": "Smoke test drafted plan",
        "a2a_transcript": [],
        "pending_po": {}
    }

    # Write dummy state to test thread_id
    graph.update_state(config, dummy_state)

    # Read state back
    saved_state = graph.get_state(config)

    assert saved_state is not None, "Saved state should not be None"
    assert saved_state.values.get("tenant_id") == "Tenant_A"
    assert saved_state.values.get("drafted_plan") == "Smoke test drafted plan"
    assert saved_state.values.get("status") == "init"
