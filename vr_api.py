# vr_api.py
"""
VR API Bridge — Sprint S15
Exposes warehouse_vision and document_vision over HTTP for the Quest WebXR front-end.
Run alongside Streamlit:  uvicorn vr_api:app --port 8502 --reload
"""
import base64
import io
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import your existing modules
from warehouse_vision import analyze_shelf_image
from document_vision import extract_document_data

app = FastAPI(title="Supply Chain VR API")

# Allow Quest browser + local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten to your GitHub Pages URL before demo
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

class ImagePayload(BaseModel):
    image_b64: str          # base64-encoded JPEG from Quest camera
    mime_type: str = "image/jpeg"

@app.get("/health")
def health():
    return {"status": "ok", "version": "S15"}

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
        result = analyze_shelf_image(image_bytes)
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
        result = extract_document_data(image_bytes)
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
