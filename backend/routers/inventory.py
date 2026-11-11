"""Inventory endpoint router for Sovereign Supply Chain."""

from fastapi import APIRouter, Query
from typing import Dict, Any, List
import db

router = APIRouter()

@router.get("/inventory")
async def get_inventory(tenant_id: str = Query("Tenant_A")):
    """Returns current inventory items for the requested tenant."""
    rows = db.execute_query(
        "SELECT item_name, quantity, supplier_id FROM inventory WHERE tenant_id = ? ORDER BY id ASC",
        (tenant_id,)
    )
    items: List[Dict[str, Any]] = []
    for r in rows:
        qty = r.get("quantity", 0)
        if qty == 0:
            status = "stockout"
        elif qty < 100:
            status = "low"
        else:
            status = "ok"
        items.append({
            "name": r.get("item_name", ""),
            "quantity": qty,
            "status": status,
            "supplier": r.get("supplier_id", "")
        })
    return {"items": items}
