"""Inventory and KPI endpoint router for Sovereign Supply Chain."""

import os
import json
import re
from fastapi import APIRouter, Query
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage
from llm_client import get_llm
import db
from demand_forecaster import calculate_sku_reorder_point

router = APIRouter()


@router.get("/inventory")
async def get_inventory(tenant_id: str = Query("Tenant_A")):
    """Returns current inventory items for the requested tenant with computed reorder_point."""
    rows = db.execute_query(
        "SELECT item_name, quantity, supplier_id FROM inventory WHERE tenant_id = ? ORDER BY id ASC",
        (tenant_id,)
    )
    items: List[Dict[str, Any]] = []
    for r in rows:
        qty = r.get("quantity", 0)
        sku = r.get("item_name", "")
        if qty == 0:
            status = "stockout"
        elif qty < 100:
            status = "low"
        else:
            status = "ok"

        # Calculate or lookup reorder point
        reorder_info = calculate_sku_reorder_point(sku, qty)
        reorder_pt = reorder_info.get("reorder_point", 20)
        eoq = reorder_info.get("eoq", 100)

        items.append({
            "name": sku,
            "quantity": qty,
            "status": status,
            "supplier": r.get("supplier_id", ""),
            "reorder_point": reorder_pt,
            "eoq": eoq
        })
    return {"items": items}


@router.get("/kpi")
async def get_kpi(tenant_id: str = Query("Tenant_A")):
    """
    Computes from DB:
    - stockout_rate: count(qty==0) / total SKUs
    - fill_rate: count(qty>0) / total SKUs
    - low_stock_rate: count(0 < qty <= 10) / total SKUs
    Then calls muse-spark-1.3:
    "Given these KPIs: {kpis}, provide a 1-sentence supply chain health summary and a risk rating: green/yellow/red."
    """
    demo = os.environ.get("DEMO_MODE") == "1"

    rows = db.execute_query(
        "SELECT quantity FROM inventory WHERE tenant_id = ?",
        (tenant_id,)
    )
    total = len(rows)
    if total == 0:
        return {
            "stockout_rate": 0.0,
            "fill_rate": 1.0,
            "low_stock_rate": 0.0,
            "summary": "No inventory registered for this tenant.",
            "risk_rating": "green"
        }

    stockouts = sum(1 for r in rows if r.get("quantity", 0) == 0)
    fill = sum(1 for r in rows if r.get("quantity", 0) > 0)
    low_stock = sum(1 for r in rows if 0 < r.get("quantity", 0) <= 10)

    stockout_rate = round(stockouts / total, 3)
    fill_rate = round(fill / total, 3)
    low_stock_rate = round(low_stock / total, 3)

    kpis = {
        "stockout_rate": stockout_rate,
        "fill_rate": fill_rate,
        "low_stock_rate": low_stock_rate
    }

    if demo:
        risk = "yellow" if stockout_rate > 0 or low_stock_rate > 0.1 else "green"
        summary = (
            f"Supply chain operation is resilient with {fill_rate:.1%} fill rate; "
            f"{stockouts} stockout and {low_stock} low-stock SKUs require proactive monitoring."
        )
        return {
            **kpis,
            "summary": summary,
            "risk_rating": risk
        }

    llm = get_llm()
    prompt = (
        f"Given these KPIs: {json.dumps(kpis)}, provide a 1-sentence supply chain health summary "
        f"and a risk rating: green/yellow/red. Return JSON: {{\"summary\": str, \"risk_rating\": \"green\"|\"yellow\"|\"red\"}}"
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        m = re.search(r"\{.*?\}", content, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
        else:
            data = json.loads(content)
        return {
            **kpis,
            "summary": str(data.get("summary", "Supply chain status evaluated.")),
            "risk_rating": str(data.get("risk_rating", "yellow")).lower()
        }
    except Exception:
        return {
            **kpis,
            "summary": f"Operations stable: {fill_rate:.1%} fill rate across {total} registered items.",
            "risk_rating": "green" if stockout_rate == 0 else "yellow"
        }
