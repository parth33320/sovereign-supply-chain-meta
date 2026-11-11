"""What-if scenario simulation router powered by muse-spark-1.3."""

import os
import json
import re
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from mcp_server import read_inventory
from llm_client import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

router = APIRouter()


class WhatIfRequest(BaseModel):
    scenario: str
    thread_id: Optional[str] = None
    tenant_id: str = "Tenant_A"


@router.post("/whatif")
async def what_if_analysis(req: WhatIfRequest):
    """
    Given current inventory state and a hypothetical scenario,
    identify which SKUs are at risk, estimated impact on stockout probability,
    and recommended mitigations.
    """
    demo = os.environ.get("DEMO_MODE") == "1"

    # Fetch inventory for tenant
    try:
        raw_inv = read_inventory(req.tenant_id)
        inventory = json.loads(raw_inv)
    except Exception:
        inventory = []

    if demo:
        return {
            "affected_skus": [
                {
                    "sku": "Widget-A",
                    "current_qty": 50,
                    "risk_level": "HIGH",
                    "days_to_stockout": 3,
                    "mitigation": "Route emergency shipment from FastShip Supply; buffer regional safety stock."
                },
                {
                    "sku": "Semiconductors",
                    "current_qty": 0,
                    "risk_level": "CRITICAL",
                    "days_to_stockout": 0,
                    "mitigation": "Activate dual-source supplier contract with Global Parts Co."
                },
                {
                    "sku": "Microcontrollers",
                    "current_qty": 8,
                    "risk_level": "MEDIUM",
                    "days_to_stockout": 5,
                    "mitigation": "Expedite transfer from secondary logistics hub."
                }
            ],
            "summary": f"Scenario '{req.scenario}' accelerates depletion across key component SKUs. Immediate buffer orders recommended."
        }

    llm = get_llm()
    system_prompt = (
        "You are a supply chain risk analyst. Given current inventory state and "
        "a hypothetical scenario, identify which SKUs are at risk, estimated impact on "
        "stockout probability, and recommended mitigations. Return JSON:\n"
        "{\n"
        "  \"affected_skus\": [\n"
        "    {\"sku\": str, \"current_qty\": int, \"risk_level\": \"HIGH\"|\"MEDIUM\"|\"LOW\"|\"CRITICAL\", \"days_to_stockout\": int, \"mitigation\": str}\n"
        "  ],\n"
        "  \"summary\": str\n"
        "}"
    )
    user_prompt = f"Current inventory: {json.dumps(inventory)}\nScenario: {req.scenario}"

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        content = response.content if isinstance(response.content, str) else str(response.content)
        m = re.search(r"\{.*?\}", content, re.DOTALL)
        if m:
            result = json.loads(m.group(0))
        else:
            result = json.loads(content)
        return result
    except Exception as e:
        return {
            "affected_skus": [
                {
                    "sku": "Widget-A",
                    "current_qty": 50,
                    "risk_level": "HIGH",
                    "days_to_stockout": 3,
                    "mitigation": "Activate emergency restock"
                }
            ],
            "summary": f"Scenario analysis completed with fallback assessment: {str(e)}"
        }
