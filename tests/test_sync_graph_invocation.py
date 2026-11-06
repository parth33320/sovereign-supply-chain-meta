import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

def test_synchronous_graph_invocation_in_app():
    """Verify that when DEMO_MODE is not set, graph is called synchronously and updates session state."""
    import streamlit.testing.v1 as st_test
    from pathlib import Path

    REPO_ROOT = Path(__file__).resolve().parent.parent
    app_path = REPO_ROOT / "app.py"

    with patch.dict(os.environ, {"DEMO_MODE": "0", "META_API_KEY": "test_key"}, clear=False), \
         patch("graph.ConnectionPool"), \
         patch("graph.get_graph_with_postgres") as mock_get_graph, \
         patch("guardrails.check_prompt_injection", return_value=True):

        mock_graph = MagicMock()
        mock_get_graph.return_value = mock_graph

        mock_result = {
            "messages": [
                HumanMessage(content="Check inventory levels"),
                AIMessage(content="[GLOBAL ORACLE ALERT] (CRITICAL): Major port strike"),
                AIMessage(content="Reallocation plan: Shift 200 units from Warehouse A to B.")
            ],
            "drafted_plan": "Reallocation plan: Shift 200 units from Warehouse A to B."
        }
        mock_graph.invoke.return_value = mock_result

        at = st_test.AppTest.from_file(str(app_path), default_timeout=10)
        at.run()

        # Submit chat input
        at.chat_input[0].set_value("Check inventory levels")
        try:
            at.run()
        except Exception:
            pass

        # Verify graph.invoke was called synchronously
        mock_graph.invoke.assert_called_once()
        invoked_state, invoked_config = mock_graph.invoke.call_args[0]

        # Verify state structure
        assert invoked_state["tenant_id"] == "Tenant_A"
        assert invoked_state["status"] == "init"
        assert len(invoked_state["messages"]) == 1
        assert isinstance(invoked_state["messages"][0], HumanMessage)
        assert invoked_state["messages"][0].content == "Check inventory levels"

        # Verify thread_id in config
        expected_thread_id = f"Tenant_A_{at.session_state['thread_id']}"
        assert invoked_config["configurable"]["thread_id"] == expected_thread_id

        # Verify responses were extracted and displayed into session_state
        chat_contents = [m["content"] for m in at.session_state["chat_history"]]
        assert "Check inventory levels" in chat_contents
        assert "[GLOBAL ORACLE ALERT] (CRITICAL): Major port strike" in chat_contents
        assert "Reallocation plan: Shift 200 units from Warehouse A to B." in chat_contents

        assert at.session_state.get("pending_plan") == "Reallocation plan: Shift 200 units from Warehouse A to B."
        assert len(at.session_state["disruption_history"]) == 1
        assert at.session_state["disruption_history"][0]["severity"] == "critical"
        assert at.session_state["disruption_history"][0]["summary"] == "Major port strike"

        # Verify pending_task_id is not set
        assert "pending_task_id" not in at.session_state
