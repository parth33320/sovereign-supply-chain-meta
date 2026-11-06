from api_resilience import with_rate_limit_retry
"""
Voice Handler Module (S4)
=========================
Provides voice ingestion, speech-to-text transcription, and logistics intent
extraction for the Sovereign Supply Chain Orchestrator.

Architecture:
- transcribe_audio: Transcribes raw audio bytes using the muse-voice-transcribe-1.0 model.
- extract_logistics_intent: Extracts structured logistics intent from transcripts using
  the Meta LLM (default: muse-spark-1.3) via ChatOpenAI.
- process_voice_input: Orchestrates transcription and intent extraction.

Inputs and Outputs:
- Input: audio_bytes (bytes)
- Output: dict with keys:
    - 'transcription': str
    - 'intent': str
    - 'status': 'ok' | 'error'
"""

import json
import io
import os
import tempfile
import logging
from typing import Dict, Any
import requests
from pydub import AudioSegment
import openai
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


@with_rate_limit_retry(max_retries=3, base_delay=2)
def transcribe_audio(audio_bytes: bytes) -> str:
    if not audio_bytes or not isinstance(audio_bytes, (bytes, bytearray)):
        raise ValueError("Invalid or empty audio bytes provided for transcription.")

    import requests
    api_key = os.environ.get("META_API_KEY")
    if not api_key:
        raise ValueError(
            "META_API_KEY is not set. "
            "Add your Meta AI API key from dev.meta.ai to your environment variables."
        )

    response = requests.post(
        "https://api.meta.ai/v1/asr/transcribe",
        headers={"Authorization": f"Bearer {api_key}"},
        files={"audio": ("audio.webm", audio_bytes, "audio/webm")},
        data={"mode": "PUSH_TO_TALK"}
    )
    response.raise_for_status()

    result = response.json()
    # handle both {text: ...} and {turns: [...]} response shapes
    if "text" in result:
        return result["text"]
    turns = result.get("turns", [])
    return " ".join(t.get("transcript", "") for t in turns).strip()


def extract_logistics_intent(transcription: str) -> str:
    """
    Extracts logistics intent from a transcript using Meta LLM.

    Inputs:
        transcription (str): Transcribed user voice speech.

    Outputs:
        str: Extracted intent or actionable logistics command representation.

    Raises:
        ValueError: If transcription is empty.
        Exception: If LLM call fails.
    """
    if not transcription or not isinstance(transcription, str) or not transcription.strip():
        raise ValueError("Empty or invalid transcription text provided for intent extraction.")

    model_name = os.environ.get("META_MODEL_NAME", "muse-spark-1.3")
    api_key = os.environ.get("META_API_KEY")
    base_url = os.environ.get("META_API_BASE_URL", "https://api.meta.ai/v1")

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0
    )

    system_prompt = (
        "You are an intelligent Logistics Voice Assistant for a Sovereign Supply Chain Orchestrator.\n"
        "Analyze the following transcribed user instruction and extract the logistics intent, "
        "including action, quantities, items/SKUs, origin, and destination if mentioned.\n"
        "Return the intent clearly, concisely, and actionably.\n\n"
        "User Transcribed Instruction:\n{transcription}\n\n"
        "Logistics Intent:"
    )

    prompt = ChatPromptTemplate.from_template(system_prompt)
    chain = prompt | llm

    response = chain.invoke({"transcription": transcription})
    return response.content.strip()


def process_voice_input(audio_bytes: bytes) -> dict:
    if not audio_bytes:
        return {"status": "error", "intent": "No audio bytes received."}

    tmp_in = None
    tmp_out = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_bytes)
            tmp_in = f.name

        segment = AudioSegment.from_file(tmp_in)
        segment = segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_out = f.name
        segment.export(tmp_out, format="wav")

        with open(tmp_out, "rb") as f:
            wav_bytes = f.read()

    except Exception as e:
        return {"status": "error", "intent": f"Audio conversion error: {e}"}
    finally:
        for p in [tmp_in, tmp_out]:
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    api_key = os.environ.get("META_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "intent": "META_API_KEY is not set. Add your Meta AI API key from dev.meta.ai to your environment variables."
        }
    base_url = os.environ.get("META_API_BASE_URL", "https://api.meta.ai/v1")

    try:
        resp = requests.post(
            f"{base_url}/asr/transcribe",
            headers={"Authorization": f"Bearer {api_key}"},
            files={
                "audio": ("audio.wav", wav_bytes, "audio/wav"),
                "request": (None, json.dumps({"model": "muse-voice-transcribe-1.0", "audioEncoding": "WAV"}), "application/json"),
            },
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        logger.warning(f"ASR BODY: {body}")
        transcription = (body.get("text") or body.get("transcription") or body.get("transcript") or " ".join(t.get("transcript","") for t in body.get("turns", []))).strip()
        if not transcription:
            return {"status": "error", "intent": "Empty transcription returned."}
        return {"status": "ok", "transcription": transcription}
    except requests.HTTPError as e:
        return {"status": "error", "intent": f"ASR HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"status": "error", "intent": str(e)}
