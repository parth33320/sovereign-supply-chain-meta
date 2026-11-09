"""Chat endpoint router for Sovereign Supply Chain."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import asyncio, uuid
import os
from guardrails import check_prompt_injection

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    tenant_id: str = "Tenant_A"

def run_graph(message: str, thread_id: str,
              tenant_id: str) -> dict:
    """Executes the LangGraph pipeline with user input and session context."""
    from graph import get_graph_with_postgres, AgentState
    from langchain_core.messages import HumanMessage
    import uuid as _uuid
    demo = os.environ.get("DEMO_MODE") == "1"
    if demo:
        # In demo mode, return simulated orchestrator analysis without live LLM call
        plan = (
            f"Orchestrator Analysis for '{message}':\n"
            f"• Tenant: {tenant_id}\n"
            f"• Stock level verified across regional hubs.\n"
            f"• Reorder recommendations drafted for review."
        )
        return {
            "messages": [HumanMessage(content=message), type("AIMsg", (), {"content": plan})()],
            "status": "awaiting_human",
            "pending_po": {
                "po_id": "PO-948201",
                "supplier": "Apex Logistics Supplier AI",
                "sku": "Widget-A",
                "quantity": 500,
                "unit_price": 8.20,
                "total_cost": 4100.0,
                "lead_time": 3
            }
        }
    graph = get_graph_with_postgres()
    state = AgentState(
        messages=[HumanMessage(content=message)],
        tenant_id=tenant_id,
        request_id=thread_id or str(_uuid.uuid4()),
    )
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(state, config=config)
    return result

@router.post("/chat")
async def chat(req: ChatRequest):
    """Processes chat messages through guardrails and the LangGraph orchestrator."""
    from backend.dependencies import get_activity_log

    if not check_prompt_injection(req.message):
        get_activity_log().append({
            "icon": "❌", "source": "guardrails",
            "msg": f"Blocked: {req.message[:40]}"
        })
        return {
            "blocked": True,
            "response": "⚠️ That input was blocked.\n\nTry:\n"
                        "• Check stock levels for Widget-A\n"
                        "• Reorder 500 Microcontrollers\n"
                        "• Emergency restock Semiconductors"
        }

    thread_id = req.thread_id or str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, run_graph, req.message, thread_id, req.tenant_id)

    messages = result.get("messages", [])
    response_text = ""
    if messages:
        last = messages[-1]
        response_text = getattr(last, "content", str(last))

    pending_po = result.get("pending_po")
    hitl_required = result.get("status") == "awaiting_human"

    get_activity_log().append({
        "icon": "🚀", "source": "orchestrator",
        "msg": "Graph execution complete"
    })

    return {
        "blocked": False,
        "response": response_text,
        "thread_id": thread_id,
        "hitl_required": hitl_required,
        "pending_po": pending_po,
    }
