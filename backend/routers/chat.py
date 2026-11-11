"""Chat endpoint router for Sovereign Supply Chain."""

import asyncio
import json
import os
import uuid
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from guardrails import check_prompt_injection
import cancel_registry

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    tenant_id: str = "Tenant_A"


@router.delete("/chat/{thread_id}")
async def cancel_chat(thread_id: str):
    """Signals cancellation for the graph running on thread_id."""
    cancel_registry.cancel(thread_id)
    return {"status": "cancelled"}


def run_graph(message: str, thread_id: str,
              tenant_id: str, event_callback=None) -> dict:
    """Executes the LangGraph pipeline with user input and session context."""
    from graph import get_graph_with_postgres, AgentState
    from langchain_core.messages import HumanMessage
    import uuid as _uuid

    demo = os.environ.get("DEMO_MODE") == "1"

    # Step transitions definition
    transitions = [
        ("global_oracle", "Scanning disruptions..."),
        ("fetch_inventory", "Fetching inventory..."),
        ("a2a_negotiate", "Negotiating with suppliers..."),
        ("draft_plan", "Drafting logistics plan..."),
        ("human_review", "Awaiting human approval..."),
    ]

    if demo:
        # Simulate node transitions in demo mode
        for node, label in transitions:
            if cancel_registry.is_cancelled(thread_id):
                return {"status": "cancelled"}
            if event_callback:
                event_callback(node, label)
            import time
            time.sleep(0.3)

        if cancel_registry.is_cancelled(thread_id):
            return {"status": "cancelled"}

        plan = (
            f"Orchestrator Analysis for '{message}':\n"
            f"• Tenant: {tenant_id}\n"
            f"• Stock level verified across regional hubs.\n"
            f"• Reorder recommendations drafted for review."
        )
        quotes = [
            {"supplier": "FastShip Supply", "price_per_unit": 8.10, "lead_time_days": 3, "minimum_order_qty": 100, "notes": "Priority lane restock"},
            {"supplier": "Apex Logistics", "price_per_unit": 8.50, "lead_time_days": 4, "minimum_order_qty": 200, "notes": "Standard express freight"},
            {"supplier": "Global Parts Co", "price_per_unit": 8.75, "lead_time_days": 6, "minimum_order_qty": 500, "notes": "Bulk discount applied"}
        ]
        recommendation = {
            "selected_supplier": "FastShip Supply",
            "reasoning": "FastShip Supply offers the lowest unit cost ($8.10) and lowest lead time (3 days), comfortably meeting the 5-day constraint."
        }
        return {
            "messages": [HumanMessage(content=message), type("AIMsg", (), {"content": plan})()],
            "status": "awaiting_human",
            "pending_po": {
                "po_id": "PO-948201",
                "supplier": "FastShip Supply",
                "sku": "Widget-A",
                "quantity": 500,
                "unit_price": 8.10,
                "total_cost": 4050.0,
                "lead_time": 3,
                "savings": "250",
                "quotes": quotes,
                "recommendation": recommendation
            }
        }

    graph = get_graph_with_postgres()
    state = AgentState(
        messages=[HumanMessage(content=message)],
        tenant_id=tenant_id,
        request_id=thread_id or str(_uuid.uuid4()),
    )
    config = {"configurable": {"thread_id": thread_id}}

    # Stream graph events if event_callback is provided
    result = None
    node_labels = {
        "global_oracle_and_forecast": ("global_oracle", "Scanning disruptions..."),
        "global_oracle": ("global_oracle", "Scanning disruptions..."),
        "fetch_inventory": ("fetch_inventory", "Fetching inventory..."),
        "a2a_negotiate": ("a2a_negotiate", "Negotiating with suppliers..."),
        "draft_plan": ("draft_plan", "Drafting logistics plan..."),
        "human_review": ("human_review", "Awaiting human approval..."),
        "draft_po": ("draft_plan", "Drafting logistics plan..."),
    }

    try:
        for event in graph.stream(state, config=config):
            if cancel_registry.is_cancelled(thread_id):
                return {"status": "cancelled"}
            for node_name, node_output in event.items():
                if event_callback and node_name in node_labels:
                    mapped_node, mapped_label = node_labels[node_name]
                    event_callback(mapped_node, mapped_label)
                result = node_output
        return result or {}
    except Exception as e:
        if cancel_registry.is_cancelled(thread_id):
            return {"status": "cancelled"}
        raise e


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE streaming endpoint for node progress and completion."""
    from backend.dependencies import get_activity_log

    thread_id = req.thread_id or str(uuid.uuid4())
    if not cancel_registry.is_cancelled(thread_id):
        cancel_registry.register(thread_id)

    async def event_generator():
        try:
            if not check_prompt_injection(req.message):
                get_activity_log().append({
                    "icon": "❌", "source": "guardrails",
                    "msg": f"Blocked: {req.message[:40]}"
                })
                payload = {
                    "blocked": True,
                    "response": "⚠️ That input was blocked.\n\nTry:\n"
                                "• Check stock levels for Widget-A\n"
                                "• Reorder 500 Microcontrollers\n"
                                "• Emergency restock Semiconductors"
                }
                yield f"data: {json.dumps(payload)}\n\n"
                return

            event_queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def queue_callback(node: str, label: str):
                loop.call_soon_threadsafe(event_queue.put_nowait, (node, label))

            future = loop.run_in_executor(
                None, run_graph, req.message, thread_id, req.tenant_id, queue_callback
            )

            while not future.done():
                if cancel_registry.is_cancelled(thread_id):
                    yield 'data: {"node": "cancelled", "label": "Request cancelled."}\n\n'
                    # Wait for thread to terminate
                    try:
                        await future
                    except Exception:
                        pass
                    return
                try:
                    node, label = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    yield f'data: {{"node": "{node}", "label": "{label}"}}\n\n'
                except asyncio.TimeoutError:
                    continue

            result = await future

            if cancel_registry.is_cancelled(thread_id) or (isinstance(result, dict) and result.get("status") == "cancelled"):
                yield 'data: {"node": "cancelled", "label": "Request cancelled."}\n\n'
                return

            # Drain remaining queued events
            while not event_queue.empty():
                node, label = event_queue.get_nowait()
                yield f'data: {{"node": "{node}", "label": "{label}"}}\n\n'

            messages = result.get("messages", [])
            response_text = ""
            if messages:
                last = messages[-1]
                response_text = getattr(last, "content", str(last))

            pending_po = result.get("pending_po")
            hitl_required = result.get("status") == "awaiting_human" or pending_po is not None

            get_activity_log().append({
                "icon": "🚀", "source": "orchestrator",
                "msg": "Graph execution complete"
            })

            final_payload = {
                "blocked": False,
                "response": response_text,
                "thread_id": thread_id,
                "hitl_required": hitl_required,
                "pending_po": pending_po,
                "node": "complete"
            }
            yield f"data: {json.dumps(final_payload)}\n\n"
        finally:
            cancel_registry.cleanup(thread_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/chat")
async def chat(req: ChatRequest):
    """Processes chat messages through guardrails and the LangGraph orchestrator (standard JSON fallback)."""
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
    cancel_registry.register(thread_id)
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, run_graph, req.message, thread_id, req.tenant_id
        )

        if cancel_registry.is_cancelled(thread_id) or result.get("status") == "cancelled":
            return {
                "blocked": False,
                "response": "Request cancelled.",
                "thread_id": thread_id,
                "cancelled": True,
                "hitl_required": False,
                "pending_po": None,
            }

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
    finally:
        cancel_registry.cleanup(thread_id)
