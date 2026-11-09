"""Voice transcription router for Sovereign Supply Chain."""

from fastapi import APIRouter, UploadFile, File

router = APIRouter()

def transcribe_audio(data: bytes) -> str:
    """Transcribes audio data using voice handler."""
    from voice_handler import transcribe_audio as _t
    return _t(data)

@router.post("/voice")
async def voice(file: UploadFile = File(...)):
    """Accepts uploaded voice recording audio file and returns transcription."""
    data = await file.read()
    transcript = transcribe_audio(data)
    return {"transcript": transcript}
