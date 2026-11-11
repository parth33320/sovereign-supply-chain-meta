"""Upload router for multimodal document, image, and voice processing."""

import os
from fastapi import APIRouter, UploadFile, File

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "application/pdf", "audio/wav", "audio/mpeg",
    "audio/ogg", "audio/mp4"
}
MAX_SIZE = 10 * 1024 * 1024  # 10MB


def transcribe_audio(file_bytes: bytes) -> str:
    """Invokes voice handler transcription."""
    from voice_handler import transcribe_audio as _transcribe
    return _transcribe(file_bytes)


def extract_document_data(file_bytes: bytes, prompt: str = None) -> dict:
    """Invokes document vision extraction."""
    from document_vision import extract_document_data as _extract
    return _extract(file_bytes, prompt=prompt) if prompt else _extract(file_bytes)


def analyze_shelf_image(file_bytes: bytes) -> dict:
    """Invokes warehouse vision analysis on uploaded shelf image."""
    from warehouse_vision import analyze_shelf_image as _analyze
    return _analyze(file_bytes)


def classify_image(file_bytes: bytes, filename: str, demo_mode: bool) -> str:
    """Classifies an image as either warehouse shelf or shipping invoice."""
    if demo_mode:
        return "shelf" if "shelf" in (filename or "").lower() else "invoice"
    result = extract_document_data(
        file_bytes,
        prompt="Classify this image. Reply with exactly one word: 'shelf' or 'invoice'"
    )
    text = (result.get("raw", "") or "").strip().lower()
    return "shelf" if "shelf" in text else "invoice"


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Receives and processes multimodal file uploads safely."""
    demo = os.environ.get("DEMO_MODE") == "1"

    if file.content_type not in ALLOWED_TYPES:
        return {
            "type": "error",
            "error": f"Unsupported file type: {file.content_type}. Use PNG, JPG, PDF, or WAV."
        }

    try:
        data = await file.read()
    except Exception:
        return {
            "type": "error",
            "error": "Could not read file. Please try again."
        }

    if len(data) > MAX_SIZE:
        return {
            "type": "error",
            "error": "File exceeds 10MB limit."
        }

    ct = (file.content_type or "").lower()
    fname = (file.filename or "").lower()

    # Audio → transcription
    if ct.startswith("audio/") or fname.endswith((".wav", ".mp3", ".ogg")):
        try:
            if demo:
                transcript = "Emergency restock Widget-A"
            else:
                transcript = transcribe_audio(data)
            return {"type": "audio", "transcript": transcript}
        except Exception:
            return {
                "type": "error",
                "error": "Voice transcription unavailable. Try typing your command instead."
            }

    # PDF → document extraction
    if ct == "application/pdf" or fname.endswith(".pdf"):
        try:
            if demo:
                result = {
                    "supplier": "Demo Supplier Ltd",
                    "total": "$4,500.00",
                    "date": "2026-11-10",
                    "items": [{"name": "Widget-A", "qty": 100, "price": "$45.00"}]
                }
            else:
                result = extract_document_data(data)
            return {"type": "invoice", "extraction": result}
        except Exception:
            return {
                "type": "error",
                "error": "Document extraction failed. Try uploading a clearer image."
            }

    # Image → classify then route
    try:
        file_type = classify_image(data, fname, demo)
    except Exception:
        return {
            "type": "ambiguous",
            "error": None,
            "message": "Could not classify image automatically."
        }

    if file_type == "shelf":
        try:
            if demo:
                result = {
                    "segments": [
                        {"label": "Widget-A", "fill_pct": 20, "status": "LOW"},
                        {"label": "Semiconductors", "fill_pct": 0, "status": "EMPTY"},
                        {"label": "Microcontrollers", "fill_pct": 75, "status": "OK"},
                    ],
                    "summary": "2 items need restocking"
                }
            else:
                result = analyze_shelf_image(data)
            return {"type": "shelf", "analysis": result, "error": None}
        except Exception:
            return {
                "type": "error",
                "error": "Shelf analysis failed. Ensure the image shows a warehouse shelf clearly."
            }
    else:
        try:
            if demo:
                result = {
                    "supplier": "FastFreight Logistics",
                    "total": "$4,500.00",
                    "date": "2026-11-10",
                    "items": [{"name": "Microcontrollers 32-bit", "qty": 100, "price": "$45.00"}]
                }
            else:
                result = extract_document_data(data)
            return {"type": "invoice", "extraction": result, "error": None}
        except Exception:
            return {
                "type": "error",
                "error": "Invoice extraction failed. Try uploading a clearer image of the invoice."
            }
