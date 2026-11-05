import json
import sqlite3
import random
from typing import Annotated, Any, Dict, List, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
import os
import tenacity
from disruption_radar import fetch_disruption_alert
from demand_forecaster import forecast_sku_stockouts

# Ensure task logging function
def log_task(request_id: str, status: str, payload: str):
    from db import get_db_connection
    conn, engine = get_db_connection()
    try:
        if engine == "postgres":
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE IF NOT EXISTS task_queue (id SERIAL PRIMARY KEY, request_id TEXT, status TEXT, payload TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
                cur.execute(
                    "INSERT INTO task_queue (request_id, status, payload) VALUES (%s, %s, %s)",
                    (request_id, status, payload)
                )
        else:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS task_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT, status TEXT, payload TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            cursor.execute(
                "INSERT INTO task_queue (request_id, status, payload) VALUES (?, ?, ?)",
                (request_id, status, payload)
            )
            conn.commit()
    finally:
        conn.close()

# DPO Logger
def log_dpo(prompt: str, chosen: str, rejected: str):
    data = {
        "prompt": prompt,
        "chosen": chosen,
        "rejected": rejected
    }
    with open("dpo_training_data.json", "a") as f:
        f.write(json.dumps(data) + "\n")

# State definition
class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], "add"]
    tenant_id: str
    request_id: str
    inventory_data: List[Dict[str, Any]]
    drafted_plan: str
    status: str
    unknown_item: str
    # Sprint-3 additions
    a2a_transcript: List[Dict[str, Any]] # running negotiation log
    pending_po: Dict[str, Any] # final Purchase Order
    # CEO-to-click portfolio additions
    work_item_id: str
    last_saving: Any

def extract_item_candidates(user_message: str) -> List[str]:
    """
    Extracts potential item or SKU names from user's message.
    """
    import re
    candidates = []

    # Quoted items: 'Item Name' or "Item Name"
    quoted = re.findall(r"['\"]([^'\"]+)['\"]", user_message)
    for q in quoted:
        if q.strip():
            candidates.append(q.strip())

    # Explicit SKU/item labels like "SKU: XYZ", "item: XYZ", "sku-1234", "SKU_1234"
    explicit = re.findall(r"\b(?:sku|item|part|product)(?:\s*(?:name|id|code)?\s*[:#\-]?\s*|\s+)([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)*)", user_message, re.IGNORECASE)
    for exp in explicit:
        cleaned = exp.strip()
        cleaned = re.sub(r"[.,;!?]+$", "", cleaned).strip()
        cleaned = re.split(r"\s+(?:in|from|to|for|with|and|or|at)\s+", cleaned, flags=re.IGNORECASE)[0].strip()
        if cleaned:
            candidates.append(cleaned)

    # Patterns like "units of X", "pieces of X", "reallocate X", "order X", "restock X"
    quantified = re.findall(r"\b(?:units|boxes|pallets|pieces|quantity)\s+of\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)*)", user_message, re.IGNORECASE)
    for q_item in quantified:
        cleaned = q_item.strip()
        cleaned = re.sub(r"[.,;!?]+$", "", cleaned).strip()
        cleaned = re.split(r"\s+(?:in|from|to|for|with|and|or|at)\s+", cleaned, flags=re.IGNORECASE)[0].strip()
        if cleaned:
            candidates.append(cleaned)

    # Patterns like SKU-[A-Z0-9-]+
    skus = re.findall(r"\b[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+\b", user_message)
    for s in skus:
        if s.lower() not in ["meta-api", "tenant-a", "tenant-b", "pre-commit", "post-hitl"]:
            candidates.append(s)

    seen = set()
    unique_candidates = []
    for c in candidates:
        if c.lower() not in seen:
            seen.add(c.lower())
            unique_candidates.append(c)

    return unique_candidates

def validate_inventory_items(state: AgentState) -> Dict:
    """
    Validates any item/SKU extracted from the user message against inventory_data.
    If an item is specified but not found in inventory_data, returns an AIMessage:
    'Item '[name]' not found in inventory. Please retry or request manager approval to add new item'
    and sets status to 'item_not_found'.
    """
    inventory = state.get("inventory_data", [])
    messages = list(state.get("messages", []))

    user_message = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
    if not user_message:
        return {}

    inventory_names = [item.get("item_name", "").strip() for item in inventory if item.get("item_name")]
    inventory_names_lower = {name.lower(): name for name in inventory_names}

    candidates = extract_item_candidates(user_message)

    for candidate in candidates:
        cand_lower = candidate.lower()
        if cand_lower in inventory_names_lower:
            continue
        if any(cand_lower in name_lower or name_lower in cand_lower for name_lower in inventory_names_lower):
            continue

        msg_text = f"Item '{candidate}' not found in inventory. Please retry or request manager approval to add new item"
        messages.append(AIMessage(content=msg_text))
        return {
            "messages": messages,
            "status": "item_not_found",
            "unknown_item": candidate
        }

    return {"status": state.get("status", "init")}

# Node 1: Global Oracle (Prescriptive Analytics Stub)
def global_oracle(state: AgentState) -> Dict:
    messages = list(state.get("messages", []))

    disruption = fetch_disruption_alert()
    if disruption.get("alert"):
        severity = str(disruption.get("severity", "low")).upper()
        summary = disruption.get("summary", "")
        messages.append(AIMessage(content=f"[GLOBAL ORACLE ALERT] ({severity}): {summary}"))

    return {"messages": messages}

# Node 1.5: Demand Forecaster Node
def forecast_demand(state: AgentState) -> Dict:
    messages = list(state.get("messages", []))
    forecasts = forecast_sku_stockouts()

    for item in forecasts:
        confidence = str(item.get("confidence", "low")).lower()
        if confidence == "high":
            sku = item.get("sku")
            days = item.get("days_until_stockout")
            messages.append(
                AIMessage(
                    content=f"[DEMAND FORECAST ALERT] ({confidence.upper()}): {sku} predicted stockout in {days} days."
                )
            )

    return {"messages": messages}

# Node 2: MCP Inventory Query (with Exponential Backoff)
@tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
    stop=tenacity.stop_after_attempt(3),
    retry=tenacity.retry_if_exception_type(Exception)
)
def fetch_inventory(state: AgentState) -> Dict:
    from mcp_server import read_inventory
    import time

    import os
    if os.environ.get("CHAOS_DROP_CONNECTION") == "1":
        if random.random() < 0.7:
            raise ConnectionError("MCP Connection unexpectedly dropped! (Chaos Test)")

    result_json = read_inventory(state["tenant_id"])
    try:
        inventory = json.loads(result_json)
    except Exception:
        inventory = []

    messages = list(state.get("messages", []))
    messages.append(AIMessage(content=f"Fetched inventory for {state['tenant_id']}: {len(inventory)} items found."))
    return {"inventory_data": inventory, "messages": messages}

# Node 3: Plan Drafter
def draft_plan(state: AgentState) -> Dict:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    inventory = state.get("inventory_data", [])
    messages = list(state.get("messages", []))

    # Extract the user's specific request
    user_request = next((m.content for m in messages if isinstance(m, HumanMessage)), "")

    if not inventory:
        plan = "No inventory found to process."
    else:
        # Instantiate ChatModel
        llm = ChatOpenAI(
            model=os.environ.get("META_MODEL_NAME", "muse-spark-1.3"),
            api_key=os.environ.get("META_API_KEY"),
            base_url=os.environ.get("META_API_BASE_URL"),
            temperature=0
        )

        # Construct dynamic system prompt
        system_prompt = """You are an intelligent Supply Chain Orchestrator.
Your goal is to draft a logistics reallocation plan based on the provided inventory data and the user's specific request.

Inventory Data:
{inventory_data}

User Request:
{user_request}

Based on this, draft a specific, actionable, and logical reallocation plan. Only output the plan.
"""
        prompt = ChatPromptTemplate.from_template(system_prompt)
        chain = prompt | llm

        inventory_str = json.dumps(inventory, indent=2)

        response = chain.invoke({
            "inventory_data": inventory_str,
            "user_request": user_request
        })

        plan = f"Plan: {response.content}"

    messages.append(AIMessage(content=f"Drafted Plan: {plan}"))

    log_task(state["request_id"], "DRAFTED", json.dumps({"plan": plan}))

    return {"drafted_plan": plan, "messages": messages, "status": "drafted"}

# HITL Dummy Node
def human_review(state: AgentState) -> Dict:
    return {}

# Node 4: Executor (Post-HITL)
def execute_plan(state: AgentState) -> Dict:
    import re
    from portfolio import record_agent_action

    messages = list(state.get("messages", []))
    messages.append(AIMessage(content="Plan executed successfully."))
    log_task(state["request_id"], "EXECUTED", "Plan executed.")

    # Record agent action in portfolio if work_item_id is present
    work_item_id = state.get("work_item_id")
    if work_item_id:
        # action_description = last message content summary
        last_msg = messages[-1].content if messages else "Plan executed successfully."
        action_description = f"Action completed: {str(last_msg)[:120]}"

        # saving_usd = extract dollar figure from state["last_saving"] if present
        raw_saving = state.get("last_saving")
        saving_usd = 0.0
        if raw_saving is not None:
            if isinstance(raw_saving, (int, float)):
                saving_usd = float(raw_saving)
            else:
                raw_str = str(raw_saving)
                # Match dollar patterns like $5,000 or 5000 or 5000.00
                m = re.search(r"\$?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)", raw_str)
                if m:
                    try:
                        saving_usd = float(m.group(1).replace(",", ""))
                    except Exception:
                        saving_usd = 0.0

        record_agent_action(work_item_id, action_description, saving_usd)

    return {"messages": messages, "status": "executed"}

def a2a_negotiate_sync(state: AgentState) -> Dict:
    """
    Synchronous implementation of multi-agent handshake between a Buyer Agent
    and a Supplier Agent using two distinct Meta model personas.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    inventory      = state.get("inventory_data", [])
    messages       = list(state.get("messages", []))
    a2a_transcript = list(state.get("a2a_transcript", []))

    # Identify SKUs that are stocked-out
    stockouts = [item for item in inventory if item.get("quantity", 0) == 0]
    if not stockouts:
        return {}            # nothing to negotiate

    stockouts_str = json.dumps(stockouts, indent=2)

    llm = ChatOpenAI(
        model=os.environ.get("META_MODEL_NAME", "muse-spark-1.3"),
        api_key=os.environ.get("META_API_KEY"),
        base_url=os.environ.get("META_API_BASE_URL"),
        temperature=0
    )

    # Step 1: Buyer Agent persona generates formal RFQ
    buyer_prompt_tmpl = ChatPromptTemplate.from_messages([
        ("system", "You are a procurement buyer. Given these stockouts, write a formal RFQ specifying items, quantities needed, and maximum acceptable lead time."),
        ("human", "Stockout items:\n{stockouts}")
    ])
    buyer_chain = buyer_prompt_tmpl | llm
    rfq_str = buyer_chain.invoke({"stockouts": stockouts_str}).content

    a2a_transcript.append({
        "role": "buyer_agent",
        "request": stockouts,
        "response": rfq_str
    })
    messages.append(AIMessage(content=f"Buyer Agent RFQ drafted:\n{rfq_str}"))

    # Step 2: Supplier Agent persona responds with structured quote JSON
    supplier_prompt_tmpl = ChatPromptTemplate.from_messages([
        ("system", "You are a supplier agent. Given this RFQ, respond with ONLY valid JSON: {{\"restock_quantity\": <number>, \"price_per_unit\": <number>, \"lead_time_days\": <number>}}"),
        ("human", "Request for Quotation:\n{rfq}")
    ])
    supplier_chain = supplier_prompt_tmpl | llm
    quote_str = supplier_chain.invoke({"rfq": rfq_str}).content

    try:
        quote_json = json.loads(quote_str)
    except Exception:
        import re
        match = re.search(r"\{.*?\}", quote_str, re.DOTALL)
        if match:
            try:
                quote_json = json.loads(match.group(0))
            except Exception:
                quote_json = {}
        else:
            quote_json = {}

    # Record the supplier exchange
    a2a_transcript.append({
        "role":      "supplier_agent",
        "request":   rfq_str,
        "response":  quote_json
    })
    messages.append(AIMessage(content=f"Supplier Agent quote received: {quote_json}"))
    return {"a2a_transcript": a2a_transcript, "messages": messages}

async def a2a_negotiate(state: AgentState) -> Dict:
    """Async wrapper around a2a_negotiate_sync."""
    import asyncio
    return await asyncio.to_thread(lambda: a2a_negotiate_sync(state))

def draft_po(state: AgentState) -> Dict:
    """
    Converts the Supplier quote into a formal PO dictionary and stores it.
    """
    import random
    a2a_transcript = state.get("a2a_transcript", [])
    if not a2a_transcript:
        return {}

    latest = a2a_transcript[-1]
    quote  = latest.get("response", {})
    po = {
        "po_id":           f"PO-{random.randint(100000, 999999)}",
        "items":           latest.get("request", []),
        "restock_quantity": quote.get("restock_quantity"),
        "price_per_unit":   quote.get("price_per_unit"),
        "lead_time_days":   quote.get("lead_time_days"),
        "supplier":         "External Supplier Agent"
    }

    messages = list(state.get("messages", []))
    messages.append(AIMessage(content=f"Drafted Purchase Order: {json.dumps(po)}"))
    return {"pending_po": po, "messages": messages, "status": "drafted"}

# Router for Intent
def route_intent(state: AgentState):
    """
    Decide next hop after fetch_inventory.

    • If any SKU has quantity==0  ➜ a2a_negotiate
    • Else use the prior heuristic to decide between draft_plan or end
    """
    inventory = state.get("inventory_data", [])
    if any(item.get("quantity", 0) == 0 for item in inventory):
        return "a2a_negotiate"

    messages = state.get("messages", [])
    user_message = next((m.content for m in messages if isinstance(m, HumanMessage)), "").lower()

    informational_keywords = ["show", "list", "what", "how many", "level", "stock", "inventory"]
    action_keywords        = ["draft", "plan", "reallocate", "optimize", "move", "ship", "send", "update"]

    has_action = any(word in user_message for word in action_keywords)
    has_info   = any(word in user_message for word in informational_keywords)

    if has_action:
        return "draft_plan"
    elif has_info:
        return "end"
    else:
        return "draft_plan"

# Router for HITL
def route_approval(state: AgentState):
    status = state.get("status")
    if status == "approved":
        return "execute_plan"
    else:
        return "end"

# Build Graph
builder = StateGraph(AgentState)

builder.add_node("global_oracle", global_oracle)
builder.add_node("forecast_demand", forecast_demand)
builder.add_node("fetch_inventory", fetch_inventory)
builder.add_node("validate_inventory_items", validate_inventory_items)
builder.add_node("draft_plan", draft_plan)
builder.add_node("human_review", human_review)
builder.add_node("execute_plan", execute_plan)
builder.add_node("a2a_negotiate", a2a_negotiate_sync)
builder.add_node("draft_po", draft_po)

builder.set_entry_point("global_oracle")
builder.add_edge("global_oracle", "forecast_demand")
builder.add_edge("forecast_demand", "fetch_inventory")
builder.add_edge("fetch_inventory", "validate_inventory_items")

def route_after_validation(state: AgentState):
    if state.get("status") == "item_not_found":
        return "end"
    return route_intent(state)

builder.add_conditional_edges(
    "validate_inventory_items",
    route_after_validation,
    {
        "a2a_negotiate": "a2a_negotiate",
        "draft_plan": "draft_plan",
        "end": END
    }
)

builder.add_edge("a2a_negotiate", "draft_po")
builder.add_edge("draft_po", "human_review")

builder.add_edge("draft_plan", "human_review")

builder.add_conditional_edges(
    "human_review",
    route_approval,
    {
        "execute_plan": "execute_plan",
        "end": END
    }
)

builder.add_edge("execute_plan", END)

def get_graph():
    return builder.compile(interrupt_before=["human_review"])

def get_graph_with_postgres():
    DB_URI = os.environ.get("POSTGRES_DB_URI")
    if not DB_URI or not DB_URI.strip():
        # Fall back to in-memory/standard graph without Postgres checkpointer when POSTGRES_DB_URI is not set
        return builder.compile(interrupt_before=["human_review"])

    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
        "sslmode": "require",
    }

    pool = ConnectionPool(conninfo=DB_URI, max_size=20, kwargs=connection_kwargs)
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"]
    )

if __name__ == "__main__":
    graph = get_graph_with_postgres()
