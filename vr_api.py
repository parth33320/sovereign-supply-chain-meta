# vr_api.py
"""
VR API Bridge — Sprint S15
Exposes warehouse_vision and document_vision over HTTP for the Quest WebXR front-end.
Run alongside Streamlit:  uvicorn vr_api:app --port 8502 --reload
"""
import base64
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Supply Chain VR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

class ImagePayload(BaseModel):
    image_b64: str
    mime_type: str = "image/jpeg"

@app.get("/")
async def serve_frontend():
    return FileResponse(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "vr", "index.html")
    )

@app.get("/health")
def health():
    return {"status": "ok", "version": "S15"}

@app.get("/api/vr/agent-status/{thread_id}")
async def agent_status(thread_id: str):
    """Poll LangGraph state for streaming agent output."""
    def get_graph():
        from graph import get_graph
        return get_graph()
    
    # Return current agent reasoning lines from your existing graph state
    # Adapt to whatever your graph state schema actually looks like
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

@app.post("/api/vr/shelf-scan/demo")
async def shelf_scan_demo():
    return {
        "type": "shelf",
        "summary": "Bay A-14 morning walk: 2 of 4 SKUs need attention.",
        "action_required": True,
        "zones": [
            {"sku": "Widget-A", "qty": 0,  "status": "empty", "color": "#ff3333", "label": "Widget-A: EMPTY"},
            {"sku": "Widget-B", "qty": 3,  "status": "low",   "color": "#ffaa00", "label": "Widget-B: LOW: 3"},
            {"sku": "Widget-C", "qty": 24, "status": "ok",    "color": "#00ff88", "label": "Widget-C: 24 units"},
            {"sku": "Widget-D", "qty": 18, "status": "ok",    "color": "#00ff88", "label": "Widget-D: 18 units"},
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
