"""Voice transcription router for Sovereign Supply Chain."""

from fastapi import APIRouter, UploadFile, File

router = APIRouter()

def transcribe_audio(data: bytes, filename: str = None, source: str = "mic"):
    """Transcribes audio data using voice handler."""
    from voice_handler import transcribe_audio as _t
    return _t(data, filename=filename, source=source)

@router.post("/voice")
async def voice(file: UploadFile = File(...)):
    """Accepts uploaded voice recording audio file and returns transcription."""
    data = await file.read()
    res = transcribe_audio(data, filename=file.filename, source="mic")
    transcript = res.get("transcription", "") if isinstance(res, dict) else res
    return {"transcript": transcript}
