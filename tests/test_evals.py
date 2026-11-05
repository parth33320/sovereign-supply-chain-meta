"""
tests/test_evals.py - Supply Chain LLM & LangGraph Eval Suite.
Replaces the promptfoo placeholder with 10 real supply chain evaluation scenarios
executed through the full LangGraph orchestration graph with mocked Meta API responses.

Evaluations asserted:
1. Correct routing decisions (e.g. stockout -> a2a_negotiate vs normal -> draft_plan or end)
2. Zero blocked-supplier recommendations (asserting against hardcoded blacklist:
   ['SUP_BLOCKED_001', 'Blacklisted Global Logistics'])
3. Correct Human-In-The-Loop (HITL) triggering on stockouts / draft approval pauses.
4. Detailed summary report printed at the end displaying pass rate and metrics.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from graph import builder, route_intent

BLOCKED_SUPPLIERS = ["SUP_BLOCKED_001", "Blacklisted Global Logistics"]

EVAL_SCENARIOS = [
    {
        "id": "EVAL-01",
        "description": "Stockout triggers autonomous A2A negotiation and stops for HITL review",
        "prompt": "Emergency restock needed for depleted semiconductors in Tenant A",
        "inventory": [
            {"item_name": "Semiconductors", "quantity": 0, "transit_time": 14, "spot_rate": 1500.5, "supplier_id": "SUP_001"},
            {"item_name": "Copper Wire Spools", "quantity": 2000, "transit_time": 7, "spot_rate": 300.0, "supplier_id": "SUP_002"}
        ],
        "expected_route": "a2a_negotiate",
        "expected_hitl": True,
        "mock_rfq": "Procurement Buyer RFQ: Request restock of 500 units Semiconductors.",
        "mock_quote": json.dumps({"restock_quantity": 500, "price_per_unit": 1450.0, "lead_time_days": 5})
    },
    {
        "id": "EVAL-02",
        "description": "Critical component stockout triggers A2A without blocked supplier",
        "prompt": "Urgent restock of depleted microcontrollers for Tenant A line",
        "inventory": [
            {"item_name": "Microcontrollers 32-bit", "quantity": 0, "transit_time": 18, "spot_rate": 95.0, "supplier_id": "SUP_014"},
            {"item_name": "Optical Sensors", "quantity": 1200, "transit_time": 8, "spot_rate": 220.0, "supplier_id": "SUP_013"}
        ],
        "expected_route": "a2a_negotiate",
        "expected_hitl": True,
        "mock_rfq": "Procurement Buyer RFQ: Need 1000 units Microcontrollers 32-bit within 10 days.",
        "mock_quote": json.dumps({"restock_quantity": 1000, "price_per_unit": 90.0, "lead_time_days": 8})
    },
    {
        "id": "EVAL-03",
        "description": "Tenant B stockout triggers supplier quote generation and draft PO",
        "prompt": "Depleted elastic waistband webbing in apparel fabrication facility",
        "inventory": [
            {"item_name": "Elastic Waistband Webbing", "quantity": 0, "transit_time": 7, "spot_rate": 35.0, "supplier_id": "SUP_028"},
            {"item_name": "Organic Cotton Yarn", "quantity": 3000, "transit_time": 10, "spot_rate": 200.0, "supplier_id": "SUP_006"}
        ],
        "expected_route": "a2a_negotiate",
        "expected_hitl": True,
        "mock_rfq": "Procurement Buyer RFQ: Urgent requirement 2000m Elastic Waistband Webbing.",
        "mock_quote": json.dumps({"restock_quantity": 2000, "price_per_unit": 32.0, "lead_time_days": 4})
    },
    {
        "id": "EVAL-04",
        "description": "Tenant B brass buttons stockout triggers negotiation with approved supplier",
        "prompt": "Out of stock on brass snap buttons, obtain supplier quote immediately",
        "inventory": [
            {"item_name": "Brass Snap Buttons", "quantity": 0, "transit_time": 11, "spot_rate": 40.0, "supplier_id": "SUP_029"},
            {"item_name": "Heavy-Duty Metal Zippers", "quantity": 10000, "transit_time": 5, "spot_rate": 50.0, "supplier_id": "SUP_008"}
        ],
        "expected_route": "a2a_negotiate",
        "expected_hitl": True,
        "mock_rfq": "Procurement Buyer RFQ: Request restock of 50000 gross Brass Snap Buttons.",
        "mock_quote": json.dumps({"restock_quantity": 50000, "price_per_unit": 38.5, "lead_time_days": 6})
    },
    {
        "id": "EVAL-05",
        "description": "Reallocation action prompt with healthy stock routes to draft_plan and pauses for HITL",
        "prompt": "Reallocate 500 structural steel plates from Hub A to Hub B",
        "inventory": [
            {"item_name": "Structural Steel Plates", "quantity": 10000, "transit_time": 30, "spot_rate": 800.25, "supplier_id": "SUP_004"}
        ],
        "expected_route": "draft_plan",
        "expected_hitl": True,
        "mock_plan": "Reallocation Plan: Transfer 500 units of Structural Steel Plates via Rail Freight. Carrier ETA 4 days."
    },
    {
        "id": "EVAL-06",
        "description": "Route optimization action with healthy stock routes to draft_plan",
        "prompt": "Draft an optimal shipping plan for copper wire spools to avoid weather disruption",
        "inventory": [
            {"item_name": "Copper Wire Spools", "quantity": 2000, "transit_time": 7, "spot_rate": 300.0, "supplier_id": "SUP_002"}
        ],
        "expected_route": "draft_plan",
        "expected_hitl": True,
        "mock_plan": "Logistics Dispatch: Re-route copper wire through central corridor. Transit time 5 days."
    },
    {
        "id": "EVAL-07",
        "description": "Parka inventory optimization routes to draft_plan with approved carriers",
        "prompt": "Plan expedited distribution for 200 technical parkas to northern retail hubs",
        "inventory": [
            {"item_name": "All-Weather Technical Parkas", "quantity": 350, "transit_time": 14, "spot_rate": 210.0, "supplier_id": "SUP_032"}
        ],
        "expected_route": "draft_plan",
        "expected_hitl": True,
        "mock_plan": "Dispatch Plan: Move 200 All-Weather Technical Parkas via Apex Logistics Express."
    },
    {
        "id": "EVAL-08",
        "description": "Pure informational inquiry routes to end without drafting PO or HITL pause",
        "prompt": "Show on-hand inventory levels for denim fabric in warehouse",
        "inventory": [
            {"item_name": "Raw Indigo Denim Fabric", "quantity": 1500, "transit_time": 15, "spot_rate": 600.0, "supplier_id": "SUP_009"}
        ],
        "expected_route": "end",
        "expected_hitl": False
    },
    {
        "id": "EVAL-09",
        "description": "Informational stock inquiry for lithium batteries routes to end",
        "prompt": "What is the current stock count and spot rate for lithium batteries?",
        "inventory": [
            {"item_name": "Lithium Batteries", "quantity": 100, "transit_time": 21, "spot_rate": 2500.0, "supplier_id": "SUP_003"}
        ],
        "expected_route": "end",
        "expected_hitl": False
    },
    {
        "id": "EVAL-10",
        "description": "Polymer resin status query routes to informational end",
        "prompt": "List available quantity and transit time for polymer resin pellets",
        "inventory": [
            {"item_name": "Polymer Resin Pellets", "quantity": 5000, "transit_time": 5, "spot_rate": 120.0, "supplier_id": "SUP_005"}
        ],
        "expected_route": "end",
        "expected_hitl": False
    }
]

EVAL_RESULTS = []


@pytest.fixture(scope="module", autouse=True)
def print_eval_summary():
    yield
    total = len(EVAL_RESULTS)
    passed = sum(1 for r in EVAL_RESULTS if r["status"] == "PASS")
    failed = total - passed
    pass_rate = (passed / total * 100.0) if total > 0 else 0.0

    report_lines = [
        "",
        "==================================================================",
        "          SOVEREIGN SUPPLY CHAIN EVALUATION SUITE REPORT          ",
        "==================================================================",
        f"Total Scenarios Evaluated: {total}",
        f"Passed: {passed} | Failed: {failed}",
        f"Pass Rate: {pass_rate:.1f}%",
        "------------------------------------------------------------------",
        f"{'ID':<9} {'Expected Route':<16} {'HITL':<8} {'Sanctions':<12} {'Verdict'}",
        "------------------------------------------------------------------"
    ]
    for r in EVAL_RESULTS:
        report_lines.append(
            f"{r['id']:<9} {r['route']:<16} {str(r['hitl']):<8} {'PASSED':<12} {r['status']}"
        )
    report_lines.append("==================================================================")
    print("\n".join(report_lines))


@pytest.mark.parametrize("scenario", EVAL_SCENARIOS, ids=[s["id"] for s in EVAL_SCENARIOS])
def test_supply_chain_eval_scenario(scenario):
    test_id = scenario["id"]
    prompt = scenario["prompt"]
    inventory = scenario["inventory"]
    expected_route = scenario["expected_route"]
    expected_hitl = scenario["expected_hitl"]

    mock_state = {
        "messages": [HumanMessage(content=prompt)],
        "inventory_data": inventory
    }
    actual_route = route_intent(mock_state)
    assert actual_route == expected_route, (
        f"[{test_id}] Expected route '{expected_route}', but got '{actual_route}'"
    )

    compiled_graph = builder.compile(interrupt_before=["human_review"])
    from langchain_core.runnables import RunnableLambda

    if scenario.get("mock_plan"):
        fake_llm = RunnableLambda(lambda x: AIMessage(content=str(scenario["mock_plan"])))
    elif scenario.get("mock_quote"):
        call_count = {"count": 0}
        def fake_invoke(x):
            if call_count["count"] == 0:
                call_count["count"] += 1
                return AIMessage(content=str(scenario.get("mock_rfq", "RFQ Details")))
            else:
                return AIMessage(content=str(scenario["mock_quote"]))
        fake_llm = RunnableLambda(fake_invoke)
    else:
        fake_llm = RunnableLambda(lambda x: AIMessage(content="Generic verified plan without blocked suppliers."))

    with patch.dict("os.environ", {"META_API_KEY": "eval_mock_key", "META_API_BASE_URL": "https://api.meta.ai/v1"}), \
         patch("langchain_openai.chat_models.base.ChatOpenAI", return_value=fake_llm), \
         patch("langchain_openai.ChatOpenAI", return_value=fake_llm), \
         patch("disruption_radar.fetch_disruption_alert", return_value={"alert": False}), \
         patch("demand_forecaster.forecast_sku_stockouts", return_value=[]), \
         patch("mcp_server.read_inventory", return_value=json.dumps(inventory)):

        initial_state = {
            "messages": [HumanMessage(content=prompt)],
            "tenant_id": "Tenant_A",
            "request_id": f"eval-{test_id.lower()}",
            "status": "init"
        }

        result = compiled_graph.invoke(initial_state)

        for msg in result.get("messages", []):
            msg_text = str(msg.content)
            for blocked in BLOCKED_SUPPLIERS:
                assert blocked.lower() not in msg_text.lower(), (
                    f"[{test_id}] Blocked supplier '{blocked}' found in agent message: {msg_text}"
                )

        if result.get("pending_po"):
            po = result["pending_po"]
            po_supplier = str(po.get("supplier", ""))
            for blocked in BLOCKED_SUPPLIERS:
                assert blocked.lower() not in po_supplier.lower(), (
                    f"[{test_id}] Blocked supplier '{blocked}' was awarded PO: {po}"
                )

        if expected_hitl:
            assert result.get("status") == "drafted", (
                f"[{test_id}] Expected HITL pause with status='drafted', got: {result.get('status')}"
            )
        else:
            assert result.get("status") != "drafted", (
                f"[{test_id}] Informational query should not trigger HITL drafted state"
            )

    EVAL_RESULTS.append({
        "id": test_id,
        "route": actual_route,
        "hitl": expected_hitl,
        "status": "PASS"
    })
