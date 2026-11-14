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

@app.post("/api/vr/shelf-scan/demo")
async def shelf_scan_demo():
    return {
        "type": "shelf",
        "summary": "Bay A-14: 3 of 6 SKUs require attention.",
        "action_required": True,
        "zones": [
            {"sku": "Semiconductors",     "qty": 0,  "status": "empty", "color": "#ff3333", "label": "Semiconductors: EMPTY"},
            {"sku": "Copper Wire Spools", "qty": 3,  "status": "low",   "color": "#ffaa00", "label": "Copper Wire Spools: LOW: 3"},
            {"sku": "Microcontrollers",   "qty": 0,  "status": "empty", "color": "#ff3333", "label": "Microcontrollers: EMPTY"},
            {"sku": "Steel Bearings",     "qty": 24, "status": "ok",    "color": "#00ff88", "label": "Steel Bearings: 24 units"},
            {"sku": "Polymer Pellets",    "qty": 18, "status": "ok",    "color": "#00ff88", "label": "Polymer Pellets: 18 units"},
            {"sku": "Circuit Boards",     "qty": 2,  "status": "low",   "color": "#ffaa00", "label": "Circuit Boards: LOW: 2"},
        ]
    }

@app.post("/api/vr/invoice-scan/demo")
async def invoice_scan_demo():
    return {
        "type": "invoice",
        "supplier": "Acme Semiconductor Co.",
        "dates": ["2026-11-10", "2026-11-18"],
        "items": [
            {"sku": "Semiconductors",   "qty": 500,  "cost": "12500.00"},
            {"sku": "Microcontrollers", "qty": 1000, "cost": "8750.00"},
        ],
        "total": "$21,250.00",
        "draft_instruction": "Approve PO for 500 Semiconductors + 1000 Microcontrollers from Acme. Delivery by Nov 18."
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
        result = _get_shelf_analyzer()(image_bytes)
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
        result = _get_invoice_extractor()(image_bytes)
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
