"""Manager endpoint router for Sovereign Supply Chain inventory governance."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import db

router = APIRouter()

class RequestAction(BaseModel):
    request_id: int

@router.get("/manager/login")
async def manager_login() -> Dict[str, str]:
    """Authenticates manager without password or token requirement."""
    return {"role": "manager"}

@router.get("/manager/pending")
async def get_manager_pending() -> List[Dict[str, Any]]:
    """Returns all pending administrative and restock requests."""
    rows = db.execute_query(
        "SELECT id, tenant_id, action, item_name, quantity, transit_time, spot_rate, supplier_id, status, created_at "
        "FROM admin_requests WHERE status = 'PENDING' ORDER BY id DESC"
    )
    return rows

@router.post("/manager/approve")
async def approve_manager_request(req: RequestAction) -> Dict[str, Any]:
    """Approves a pending manager request."""
    db.execute_mutation(
        "UPDATE admin_requests SET status = 'APPROVED' WHERE id = ?",
        (req.request_id,)
    )
    return {"status": "APPROVED", "request_id": req.request_id}

@router.post("/manager/reject")
async def reject_manager_request(req: RequestAction) -> Dict[str, Any]:
    """Rejects a pending manager request."""
    db.execute_mutation(
        "UPDATE admin_requests SET status = 'REJECTED' WHERE id = ?",
        (req.request_id,)
    )
    return {"status": "REJECTED", "request_id": req.request_id}
