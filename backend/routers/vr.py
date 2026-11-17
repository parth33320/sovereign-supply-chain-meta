"""VR/AR supply chain endpoints — A2A negotiation, invoice scan, payment."""

import os, json, hashlib
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage

from llm_client import get_llm

router = APIRouter()

# Muse status cache with key hash for invalidation on key change
_muse_cache = {"data": None, "expires": 0, "key_hash": ""}

# ── Hardcoded fallback data (used when no Muse key or DEMO_MODE=1) ────────────

FALLBACK_SUPPLIERS = [
    {"name": "Apex Logistics",   "unit_price": 8.20, "lead_days": 3, "reliability": 0.98},
    {"name": "Global Parts Co",  "unit_price": 8.75, "lead_days": 6, "reliability": 0.94},
    {"name": "FastShip Inc",     "unit_price": 9.10, "lead_days": 2, "reliability": 0.89},
]

FALLBACK_NEGOTIATION = {
    "log": [
        {"icon": "🔍", "text": "Widget-A: <strong>0 units</strong> — restock triggered"},
        {"icon": "📡", "text": "RFQ broadcast to 3 registered suppliers"},
        {"icon": "💬", "text": "Apex Logistics bid: <strong>$8.20/u · 3 days · 98% reliability</strong>"},
        {"icon": "💬", "text": "Global Parts Co bid: <strong>$8.75/u · 6 days · 94% reliability</strong>"},
        {"icon": "💬", "text": "FastShip Inc bid: <strong>$9.10/u · 2 days · 89% reliability</strong>"},
        {"icon": "🧠", "text": "Muse evaluated: cost × lead-time × reliability score"},
        {"icon": "✅", "text": "Selected: <strong>Apex Logistics</strong> — best weighted score (0.94)"},
    ],
    "winner": {
        "supplier": "Apex Logistics",
        "unit_price": 8.20,
        "lead_days": 3,
        "reasoning": "Lowest cost with high reliability. FastShip Inc is faster but 9% less reliable and 11% more expensive. Global Parts Co is slower and more expensive.",
    },
    "draft_po": {
        "po_id": "PO-2026-847",
        "supplier": "Apex Logistics",
        "sku": "Widget-A",
        "qty": 500,
        "unit_price": 8.20,
        "total": 4100.00,
        "delivery_days": 3,
    },
    "powered_by_muse": False,
}

SAM_SYSTEM_PROMPT = """You are SAM (Supply chain Autonomous Manager), a world-class supply chain expert powered by Muse.

Your job: evaluate competing supplier bids for an urgent restock and select the best one using a weighted scoring model.

Scoring weights:
- Cost: 40% (lower is better — normalize to 0-1 scale within bid set)
- Lead time: 35% (fewer days is better)
- Reliability: 25% (higher % is better)

Return a JSON object with this exact structure:
{
  "log": [
    {"icon": "🔍", "text": "..."},
    {"icon": "📡", "text": "..."},
    {"icon": "💬", "text": "...(one line per supplier bid)"},
    {"icon": "🧠", "text": "...(your scoring rationale)"},
    {"icon": "✅", "text": "...(winner announcement)"}
  ],
  "winner": {
    "supplier": "...",
    "unit_price": 0.00,
    "lead_days": 0,
    "reasoning": "..."
  },
  "draft_po": {
    "po_id": "PO-2026-847",
    "supplier": "...",
    "sku": "Widget-A",
    "qty": 500,
    "unit_price": 0.00,
    "total": 0.00,
    "delivery_days": 0
  }
}

Be concise. Use <strong> tags for key numbers in log text. No markdown outside the JSON."""


class NegotiateRequest(BaseModel):
    sku: str = "Widget-A"
    qty: int = 500
    tenant_id: str = "Tenant_A"


class InterpretVoiceRequest(BaseModel):
    transcript: str
    workflow_state: dict = {}  # {pending_po, approved_po, active_invoice, bin_status}


@router.post("/vr/negotiate")
async def negotiate(req: NegotiateRequest):
    """
    SAM agent negotiates with suppliers.
    - With META_API_KEY: calls Muse with supply chain expert system prompt
    - Without key / DEMO_MODE: returns hardcoded fallback instantly
    """
    demo = os.environ.get("DEMO_MODE") == "1"
    has_key = bool((os.environ.get("META_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip())

    if demo or not has_key:
        return {**FALLBACK_NEGOTIATION, "powered_by_muse": False}

    try:
        from llm_client import get_llm
        llm = get_llm()

        bids_text = "\n".join(
            f"- {s['name']}: ${s['unit_price']}/unit, {s['lead_days']} day lead time, {int(s['reliability']*100)}% delivery reliability"
            for s in FALLBACK_SUPPLIERS
        )

        human_msg = f"""Urgent restock needed: {req.qty}x {req.sku} (current stock: 0 units).

Supplier bids received:
{bids_text}

Evaluate these bids using your weighted scoring model and select the best supplier.
Return only the JSON object described in your instructions."""

        response = await llm.ainvoke([
            SystemMessage(content=SAM_SYSTEM_PROMPT),
            HumanMessage(content=human_msg),
        ])

        raw = response.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        result["powered_by_muse"] = True
        return result

    except Exception as e:
        # Graceful fallback if Muse call fails
        return {**FALLBACK_NEGOTIATION, "powered_by_muse": False, "error": str(e)}


@router.post("/vr/invoice-scan/{demo_id}")
async def invoice_scan(demo_id: str):
    """Simulate Muse image model scanning incoming supplier invoice."""
    return {
        "type": "invoice",
        "supplier": "Apex Logistics",
        "invoice_id": "INV-2026-847",
        "po_ref": "PO-2026-847",
        "items": [{"sku": "Widget-A", "qty": 500, "unit_price": 8.20}],
        "total": "$4,100.00",
        "po_match": True,
        "match_pct": 100,
    }


@router.post("/vr/invoice-pay/{demo_id}")
async def invoice_pay(demo_id: str):
    """Release payment after 3-way match (PO ↔ Invoice ↔ GRN)."""
    return {
        "status": "paid",
        "newQty": 500,
        "message": "3-way match verified. Payment released to Apex Logistics.",
    }


@router.post("/vr/reset-demo")
async def reset_demo():
    return {"status": "reset"}


@router.post("/vr/interpret-voice")
async def interpret_voice(req: InterpretVoiceRequest):
    """muse-spark-1.3 supply chain SME: corrects transcript + returns valid intent given workflow state."""
    state = req.workflow_state
    # Build allowed intents based on workflow state
    allowed = []
    if not state.get("pending_po"):
        allowed.append("restock")
    if state.get("pending_po") and not state.get("approved_po"):
        allowed += ["approve_po", "reject_po"]
    if state.get("approved_po") and not state.get("active_invoice"):
        allowed.append("show_invoice")
    if state.get("active_invoice"):
        allowed.append("pay_invoice")

    system = f"""You are SAM (Supply chain Autonomous Manager), a supply chain AI agent running a live warehouse demo.

DEMO WORKFLOW:
- Step 1 (RESTOCK): Widget-A bin is empty. User says "restock" or "restock Widget-A" → SAM broadcasts RFQ to 3 suppliers (Apex Logistics, Global Parts Co, FastShip Inc), evaluates bids using cost/lead-time/reliability scoring, selects winner, generates draft PO for 500 units.
- Step 2 (APPROVE or REJECT PO): User reviews Purchase Order PO-2026-847 from Apex Logistics ($8.20/unit, 500 units, $4,100 total, 3-day delivery). User says "approve PO" to authorize → moves to invoice step. Or says "reject PO" / "reject" to cancel.
- Step 3 (SHOW INVOICE): After PO approved, Widget-A shows as "inbound". User says "open invoice" or "show invoice" or taps Widget-A → SAM scans invoice via Muse image recognition.
- Step 4 (PAY INVOICE): User reviews scanned invoice. Says "pay invoice" or "pay" → SAM verifies and releases payment. Demo complete: Widget-A restocked to 500 units.

REJECTION PATH: If PO rejected at Step 2, demo resets to Step 1 (restock can be triggered again).

COMMON SPEECH-TO-TEXT ERRORS TO CORRECT:
- "widget a" / "widget eight" / "widget hey" → "Widget-A"
- "approve p o" / "approve peo" / "approve" → "approve PO"
- "reject p o" / "reject peo" → "reject PO"
- "pay in voice" / "make payment" / "release payment" → "pay invoice"
- "show in voice" / "open in voice" / "check invoice" → "open invoice"
- "restock" / "re-stock" / "order more" / "replenish" → "restock"
- "apex" / "apex logistics" / "apex log" → "Apex Logistics"

YOUR TASK:
1. Correct speech-to-text errors using your knowledge of this demo's vocabulary
2. Return the correct intent from ONLY the currently allowed actions: {allowed}
3. If the transcript doesn't match any allowed action, return intent="unknown" — do NOT suggest steps the user can't take yet

Respond ONLY with JSON: {{"intent": "<intent>", "corrected": "<corrected transcript>"}}
Valid intents: restock, approve_po, reject_po, show_invoice, pay_invoice, unknown"""

    try:
        from llm_client import get_llm
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=f"Transcript: {req.transcript}"),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        result = json.loads(raw.strip())
        return {"intent": result.get("intent", "unknown"), "corrected": result.get("corrected", req.transcript)}
    except Exception as e:
        # Fallback: keyword match
        t = req.transcript.lower()
        if "restock" in t or "widget" in t or "order" in t: intent = "restock"
        elif "approve" in t or "accept" in t: intent = "approve_po"
        elif "reject" in t or "cancel" in t: intent = "reject_po"
        elif "invoice" in t or "bill" in t: intent = "show_invoice"
        elif "pay" in t or "settle" in t: intent = "pay_invoice"
        else: intent = "unknown"
        # Only return if allowed
        if intent not in allowed: intent = "unknown"
        return {"intent": intent, "corrected": req.transcript}


@router.get("/vr/muse-status")
async def muse_status():
    """Reports whether a real Muse API key is configured and working."""
    import time
    global _muse_cache
    now = time.time()

    # Compute hash of current API key for cache invalidation on key change
    current_key = (os.environ.get("META_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    current_hash = hashlib.md5(current_key.encode()).hexdigest()

    # Check cache first (also invalidate if API key changed)
    if _muse_cache and _muse_cache.get("data") and now < _muse_cache.get("expires", 0) and _muse_cache.get("key_hash") == current_hash:
        return _muse_cache["data"]

    # No cache or expired or key changed
    demo = os.environ.get("DEMO_MODE") == "1"
    if demo:
        result = {"muse_active": False, "state": "demo"}
        _muse_cache = {"data": result, "expires": now + 300, "key_hash": current_hash}
        return result

    api_key = current_key
    if not api_key:
        result = {"muse_active": False, "state": "no_key"}
        _muse_cache = {"data": result, "expires": now + 300, "key_hash": current_hash}
        return result

    # Live check: make a tiny API call
    try:
        llm = get_llm()
        response = await llm.ainvoke("ping")
        # Success
        result = {"muse_active": True, "state": "live", "model": "muse-spark-1.3"}
        _muse_cache = {"data": result, "expires": now + 300, "key_hash": current_hash}
        return result
    except Exception as e:
        # Classify the error
        error_str = str(e).lower()
        if any(kw in error_str for kw in ["401", "403", "auth", "unauthorized", "forbidden", "invalid", "api key", "apikey", "permission"]):
            result = {"muse_active": False, "state": "invalid_key"}
        elif any(kw in error_str for kw in ["timeout", "timed out", "connection", "network", "unreachable", "refused", "no route", "host"]):
            result = {"muse_active": False, "state": "unreachable"}
        else:
            result = {"muse_active": False, "state": "error"}
        _muse_cache = {"data": result, "expires": now + 300, "key_hash": current_hash}
        return result
