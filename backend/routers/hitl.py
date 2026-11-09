"""Human-in-the-loop (HITL) approval router for purchase orders."""

from fastapi import APIRouter
from pydantic import BaseModel
from backend.dependencies import get_activity_log

router = APIRouter()

class HITLRequest(BaseModel):
    thread_id: str
    tenant_id: str = "Tenant_A"

def resume_graph(thread_id: str, approved: bool) -> dict:
    """Resumes paused LangGraph workflow with operator approval state."""
    from graph import get_graph_with_postgres
    graph = get_graph_with_postgres()
    config = {"configurable": {"thread_id": thread_id}}
    if approved:
        result = graph.invoke(None, config=config)
        return result
    return {"status": "rejected"}

@router.post("/hitl/approve")
async def approve(req: HITLRequest):
    """Approves a pending purchase order and resumes workflow."""
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, resume_graph, req.thread_id, True)
    get_activity_log().append({
        "icon": "✅", "source": "hitl",
        "msg": "PO approved by operator"
    })
    return {"status": "approved", "result": str(result)}

@router.post("/hitl/reject")
async def reject(req: HITLRequest):
    """Rejects a pending purchase order."""
    get_activity_log().append({
        "icon": "❌", "source": "hitl",
        "msg": "PO rejected by operator"
    })
    return {"status": "rejected"}
