# vr_api.py
"""
VR API Bridge — Sprint S15
Exposes warehouse_vision and document_vision over HTTP for the Quest WebXR front-end.
Run alongside Streamlit:  uvicorn vr_api:app --port 8502 --reload
"""
import base64
import json
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from db import execute_query, execute_mutation

app = FastAPI(title="Supply Chain VR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

AGENT_THREADS_DDL = """
CREATE TABLE IF NOT EXISTS agent_threads (
    thread_id TEXT PRIMARY KEY,
    transcript TEXT,
    draft_po TEXT,
    status TEXT DEFAULT 'running',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

@app.on_event("startup")
async def ensure_agent_threads_table():
    """Ensure the agent_threads table exists on existing databases."""
    execute_mutation(AGENT_THREADS_DDL)

class ImagePayload(BaseModel):
    image_b64: str
    mime_type: str = "image/jpeg"


class VoiceIntentPayload(BaseModel):
    transcript: str = ""


VOICE_INTENTS = ("restock", "approve_po", "reject_po", "pay_invoice", "show_invoice", "unknown")

VOICE_INTENT_SYSTEM_PROMPT = (
    "You are a supply chain warehouse assistant. Extract intent from voice commands. "
    "Reply with JSON only: "
    '{"intent": "restock"|"approve_po"|"reject_po"|"pay_invoice"|"show_invoice"|"unknown", '
    '"item": string|null}'
)

@app.get("/")
async def serve_frontend():
    return FileResponse(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "vr", "index.html")
    )

@app.get("/health")
def health():
    return {"status": "ok", "version": "S26"}

@app.get("/api/vr/agent-status/{thread_id}")
async def agent_status(thread_id: str):
    """Poll LangGraph state for streaming agent output, keyed by thread_id."""
    try:
        row = execute_query(
            "SELECT transcript, draft_po, status FROM agent_threads WHERE thread_id = ?",
            (thread_id,),
        )
    except Exception:
        row = []

    # No row yet: fall back to hardcoded demo strings only in DEMO_MODE
    if not row:
        if os.environ.get("DEMO_MODE") == "1":
            return {
                "lines": [
                    "🔍 Fetching inventory for Widget-A...",
                    "📡 Disruption radar: Port delays +2 days",
                    "🤝 Buyer agent: Sending RFQ to Apex Logistics",
                    "💬 Supplier agent: Quote received — $8.20/unit",
                    "✅ Negotiation complete. Best price locked.",
                ],
                "done": True,
                "draft_po": {
                    "supplier": "Apex Logistics",
                    "sku": "Widget-A",
                    "qty": 500,
                    "unit_price": 8.20,
                    "total": 4100.00,
                    "delivery_days": 3
                }
            }
        return {"lines": ["⏳ Negotiating..."], "done": False}

    data = row[0]
    status = data.get("status")
    if status == "done":
        try:
            transcript = json.loads(data.get("transcript") or "[]")
        except Exception:
            transcript = []
        try:
            draft_po = json.loads(data.get("draft_po") or "{}")
        except Exception:
            draft_po = {}

        lines = []
        for entry in transcript:
            if isinstance(entry, str):
                lines.append(entry)
                continue
            if not isinstance(entry, dict):
                continue
            role = entry.get("role", "agent")
            if role == "buyer_agent":
                lines.append("🔍 Checking inventory — Widget-A: 0 units")
                lines.append("🤝 Buyer agent: Sending RFQ to 3 suppliers")
            elif role == "supplier_agent":
                sup = entry.get("supplier", "Supplier")
                q = entry.get("quote", {})
                price = q.get("price_per_unit", 0)
                lead = q.get("lead_time_days", 0)
                lines.append(f"💬 {sup}: ${price}/unit · {lead} days")
            elif role == "procurement_analyst":
                rec = entry.get("recommendation", {})
                sel = rec.get("selected_supplier", "Apex Logistics")
                lines.append(f"✅ Best deal: {sel} — locked")
        if not lines:
            lines = ["✅ Negotiation complete. Best price locked."]
        return {"lines": lines, "done": True, "draft_po": draft_po}

    # status == "running"
    return {"lines": ["⏳ Negotiating..."], "done": False}


class AgentThreadSeed(BaseModel):
    transcript: list
    draft_po: dict


@app.post("/api/vr/agent-threads/{thread_id}")
async def seed_agent_thread(thread_id: str, payload: AgentThreadSeed):
    """Seed demo transcript + draft_po into agent_threads for polling (demo path)."""
    execute_mutation(
        "INSERT OR REPLACE INTO agent_threads (thread_id, transcript, draft_po, status) VALUES (?,?,?,?)",
        (thread_id, json.dumps(payload.transcript), json.dumps(payload.draft_po), "done")
    )
    return {"status": "seeded", "thread_id": thread_id}

@app.post("/api/vr/shelf-scan/demo")
async def shelf_scan_demo():
    return {
        "type": "shelf",
        "summary": "Bay A-14 morning walk: 2 of 4 SKUs need attention.",
        "action_required": True,
        "zones": [
            {"sku": "Widget-A", "qty": 0,  "status": "empty", "color": "#ff3333", "label": "Widget-A: EMPTY"},
            {"sku": "Widget-B", "qty": 3,  "status": "low",   "color": "#ffaa00", "label": "Widget-B: LOW: 3"},
            {"sku": "Widget-C", "qty": 18, "status": "ok",    "color": "#00ff88", "label": "Widget-C: 18 units"},
            {"sku": "Widget-D", "qty": 24, "status": "ok",    "color": "#00ff88", "label": "Widget-D: 24 units"},
        ]
    }

@app.post("/api/vr/invoice-scan/demo")
async def invoice_scan_demo():
    return {
        "type": "invoice",
        "supplier": "Apex Logistics",
        "dates": ["2026-11-14", "2026-11-17"],
        "items": [
            {"sku": "Widget-A", "qty": 500, "cost": "8.20"},
        ],
        "total": "$4,100.00",
        "draft_instruction": "Approve PO for 500x Widget-A from Apex Logistics at $8.20/unit. Delivery in 3 days."
    }


@app.get("/api/vr/inventory/demo")
async def inventory_demo():
    """Return live inventory (Tenant_A) for the AR Walk shelf UI refresh."""
    rows = execute_query(
        "SELECT item_name AS sku, quantity AS qty, tenant_id FROM inventory WHERE tenant_id = ?",
        ("Tenant_A",),
    )
    return {"items": rows}


class InvoicePayPayload(BaseModel):
    po: dict
    invoice: dict


@app.post("/api/vr/invoice-pay/demo")
async def invoice_pay_demo(payload: InvoicePayPayload):
    """
    Cross-check invoice against the approved PO; on match release payment and
    increment Widget-A stock in mock_sap.db. On mismatch, return a dispute draft
    without touching stock.
    """
    po = payload.po or {}
    inv = payload.invoice or {}
    inv_items = inv.get("items") or [{}]
    inv_unit = float(inv_items[0].get("cost", 0) or 0)
    po_unit = float(po.get("unit_price", 0) or 0)
    delta = inv_unit - po_unit
    match = abs(delta) < 0.001
    confidence = 1.0 if match else 0.0

    if not match:
        return {
            "status": "discrepancy",
            "match": False,
            "confidence": confidence,
            "delta": round(delta, 2),
            "disputeDraft": (
                f"Invoice shows ${inv_unit:.2f}/unit; PO locked ${po_unit:.2f}/unit "
                f"— requesting credit memo for the difference"
            ),
        }

    # Release payment: increment Widget-A stock by invoiced qty
    inv_qty = int((inv_items[0].get("qty") or inv.get("qty") or po.get("qty") or 0) or 0)
    execute_mutation(
        "UPDATE inventory SET quantity = quantity + ? WHERE tenant_id = ? AND item_name = ?",
        (inv_qty, "Tenant_A", "Widget-A"),
    )
    rows = execute_query(
        "SELECT quantity AS qty FROM inventory WHERE tenant_id = ? AND item_name = ?",
        ("Tenant_A", "Widget-A"),
    )
    new_qty = rows[0]["qty"] if rows else (po.get("qty", 0) + inv_qty)

    return {
        "status": "paid",
        "match": True,
        "confidence": confidence,
        "delta": None,
        "disputeDraft": None,
        "newQty": new_qty,
    }


@app.post("/api/vr/reset-demo")
async def reset_demo():
    """Restore Widget-A to its original seeded qty (50) for Tenant_A."""
    execute_mutation(
        "UPDATE inventory SET quantity = ? WHERE tenant_id = ? AND item_name = ?",
        (50, "Tenant_A", "Widget-A"),
    )
    return {"status": "reset", "item": "Widget-A", "qty": 50, "tenant_id": "Tenant_A"}


@app.post("/api/vr/shelf-scan")
async def shelf_scan(payload: ImagePayload):
    """
    Receives a base64 shelf image from the Quest,
    runs SAM 3.1 segmentation, returns AR overlay data.
    """
    try:
        image_bytes = base64.b64decode(payload.image_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image")

    try:
        from warehouse_vision import analyze_shelf_image
        result = analyze_shelf_image(image_bytes)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"warehouse_vision not available: {e}. Set META_API_KEY in .env")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shelf analysis failed: {e}")

    # Normalize result into AR overlay schema
    # analyze_shelf_image returns a dict; adapt field names to what your code actually returns
    overlay = _shelf_result_to_overlay(result)
    return overlay

@app.post("/api/vr/interpret-voice")
async def interpret_voice(payload: VoiceIntentPayload):
    """
    Classify a voice transcript into a warehouse intent via muse-spark-1.3.
    Always returns a valid {"intent": <allowed>, "item": <str|null>} object; never raises.
    """
    transcript = (payload.transcript or "").strip()[:500]
    if not transcript:
        return {"intent": "unknown", "item": None}

    api_key = os.environ.get("MUSE_API_KEY") or os.environ.get("META_API_KEY")
    if not api_key:
        return {"intent": "unknown", "item": None}

    base_url = (
        os.environ.get("MUSE_BASE_URL")
        or os.environ.get("META_API_BASE_URL")
        or "https://api.meta.ai/v1"
    ).rstrip("/")
    model = os.environ.get("MUSE_MODEL_NAME") or os.environ.get("META_MODEL_NAME") or "muse-spark-1.3"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": VOICE_INTENT_SYSTEM_PROMPT},
                        {"role": "user", "content": transcript},
                    ],
                    "max_tokens": 60,
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
    except Exception:
        return {"intent": "unknown", "item": None}

    return _parse_intent_json(content)


def _parse_intent_json(content):
    """Extract the {"intent", "item"} dict from an LLM reply, tolerating fences and prose."""
    if isinstance(content, dict):
        data = content
    else:
        text = (content or "").strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return {"intent": "unknown", "item": None}
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return {"intent": "unknown", "item": None}

    if not isinstance(data, dict):
        return {"intent": "unknown", "item": None}

    intent = str(data.get("intent", "unknown")).strip().lower()
    if intent not in VOICE_INTENTS:
        intent = "unknown"
    item = data.get("item")
    return {"intent": intent, "item": item if isinstance(item, str) else None}

@app.post("/api/vr/invoice-scan")
async def invoice_scan(payload: ImagePayload):
    """
    Receives a base64 invoice/BOL image from the Quest,
    runs Muse Image extraction, returns structured AR panel data.
    """
    try:
        image_bytes = base64.b64decode(payload.image_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image")

    try:
        from document_vision import extract_document_data
        result = extract_document_data(image_bytes)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"document_vision not available: {e}. Set META_API_KEY in .env")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invoice extraction failed: {e}")

    panel = _invoice_result_to_panel(result)
    return panel

# ── Adapters ──────────────────────────────────────────────────────────────────

def _shelf_result_to_overlay(raw: dict) -> dict:
    """
    Convert warehouse_vision output into AR overlay JSON.
    Adjust field names to match what analyze_shelf_image actually returns.
    """
    # Defensive: handle both list and dict returns
    segments = raw.get("segments") or raw.get("items") or []
    summary  = raw.get("summary") or raw.get("description") or str(raw)

    zones = []
    for seg in segments:
        status = "ok"
        sku    = seg.get("sku") or seg.get("label") or "Unknown SKU"
        qty    = seg.get("quantity") or seg.get("qty") or seg.get("count")
        if qty is not None:
            if int(qty) == 0:
                status = "empty"
            elif int(qty) < 5:
                status = "low"

        zones.append({
            "sku":    sku,
            "qty":    qty,
            "status": status,       # "ok" | "low" | "empty"
            "color":  _status_color(status),
            "label":  f"{sku}: {'EMPTY' if status=='empty' else ('LOW: '+str(qty) if status=='low' else str(qty)+' units')}",
        })

    return {
        "type":    "shelf",
        "summary": summary,
        "zones":   zones,
        "action_required": any(z["status"] in ("low","empty") for z in zones),
    }

def _invoice_result_to_panel(raw: dict) -> dict:
    """
    Convert document_vision output into AR panel JSON.
    """
    return {
        "type":     "invoice",
        "supplier": raw.get("supplier") or raw.get("vendor") or "Unknown",
        "dates":    raw.get("dates") or [],
        "items":    raw.get("items") or raw.get("line_items") or [],
        "total":    raw.get("total") or raw.get("total_cost") or "",
        "draft_instruction": raw.get("draft_instruction") or
                             f"Review invoice from {raw.get('supplier','supplier')} and approve PO.",
    }

def _status_color(status: str) -> str:
    return {"ok": "#00ff88", "low": "#ffaa00", "empty": "#ff3333"}.get(status, "#ffffff")
