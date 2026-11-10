"""Upload router for multimodal document, image, and voice processing."""

from fastapi import APIRouter, UploadFile, File, HTTPException
import os

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "application/pdf", "audio/wav", "audio/mpeg",
    "audio/ogg", "audio/mp4"
}
MAX_SIZE = 10 * 1024 * 1024  # 10MB

def classify_image(file_bytes: bytes,
                   filename: str,
                   demo_mode: bool) -> str:
    """Classifies an image as either warehouse shelf or shipping invoice."""
    if demo_mode:
        return "shelf" if "shelf" in filename.lower() else "invoice"
    from document_vision import extract_document_data
    result = extract_document_data(
        file_bytes,
        prompt="Classify this image. Reply with exactly one word: 'shelf' or 'invoice'")
    text = (result.get("raw", "") or "").strip().lower()
    return "shelf" if "shelf" in text else "invoice"

def analyze_shelf_image(file_bytes: bytes) -> dict:
    """Invokes warehouse vision analysis on uploaded shelf image."""
    from warehouse_vision import analyze_shelf_image as _analyze
    return _analyze(file_bytes)

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Receives and processes multimodal file uploads."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(400, "File exceeds 10MB limit")

    demo = os.environ.get("DEMO_MODE") == "1"
    ct = file.content_type or ""

    # Audio → voice transcription
    if ct.startswith("audio/") or file.filename.lower().endswith(".wav"):
        from voice_handler import transcribe_audio
        transcript = transcribe_audio(data)
        return {"type": "audio", "transcript": transcript}

    # PDF → document extraction
    if ct == "application/pdf":
        from document_vision import extract_document_data
        result = extract_document_data(data)
        return {"type": "invoice", "extraction": result}

    # Image → classify then route
    file_type = classify_image(data, file.filename or "", demo)
    if file_type == "shelf":
        result = analyze_shelf_image(data)
        return {"type": "shelf", "analysis": result}
    else:
        from document_vision import extract_document_data
        result = extract_document_data(data)
        return {"type": "invoice", "extraction": result}
