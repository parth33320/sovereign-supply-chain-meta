"""Voice transcription router for Sovereign Supply Chain."""

import sqlite3
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
from db import get_db_connection

router = APIRouter()


def log_voice_history(transcript: str, thread_id: Optional[str] = None):
    """Logs voice transcript, timestamp, and thread_id to voice_history table."""
    try:
        conn, engine = get_db_connection()
        if engine == "postgres":
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS voice_history "
                    "(id SERIAL PRIMARY KEY, transcript TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, thread_id TEXT)"
                )
                cur.execute(
                    "INSERT INTO voice_history (transcript, thread_id) VALUES (%s, %s)",
                    (transcript, thread_id or "")
                )
        else:
            cur = conn.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS voice_history "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, transcript TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, thread_id TEXT)"
            )
            cur.execute(
                "INSERT INTO voice_history (transcript, thread_id) VALUES (?, ?)",
                (transcript, thread_id or "")
            )
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging voice history: {e}")


def transcribe_audio(data: bytes, source: str = "mic", filename: str = "") -> dict | str:
    """Transcribes audio data using voice handler."""
    from voice_handler import process_voice_input
    result = process_voice_input(data, source=source, filename=filename)
    return result


DEMO_TRANSCRIPT = (
    "Emergency restock Widget-A — stockout detected. "
    "We need to reorder SKU WH-4821, we are below reorder threshold."
)


@router.post("/voice")
async def voice(file: UploadFile = File(...), thread_id: Optional[str] = Form(None), source: Optional[str] = Form("mic")):
    """Accepts uploaded voice recording audio file and returns transcription and intent."""
    import os
    data = await file.read()
    fname = (file.filename or "").lower()

    # Demo/fallback mode: no Muse key, demo env, or sample asset filename
    muse_key = os.environ.get("MUSE_API_KEY", "").strip()
    demo = os.environ.get("DEMO_MODE") == "1"
    is_sample = "sample-voice" in fname or "silence" in fname or not muse_key or demo

    if is_sample:
        log_voice_history(DEMO_TRANSCRIPT, thread_id)
        return {
            "status": "ok",
            "transcript": DEMO_TRANSCRIPT,
            "confidence": 1.0,
            "intent": "restock",
            "suggestion": "Proceed to reorder workflow",
            "demo_mode": True,
        }

    try:
        res = transcribe_audio(data, source=source or "mic", filename=file.filename or "")
    except Exception as exc:
        print(f"[voice] transcription error: {exc}")
        log_voice_history(DEMO_TRANSCRIPT, thread_id)
        return {
            "status": "ok",
            "transcript": DEMO_TRANSCRIPT,
            "confidence": 1.0,
            "intent": "restock",
            "suggestion": "",
            "demo_mode": True,
        }

    if isinstance(res, dict):
        transcript = res.get("transcription", "")
        status = res.get("status", "ok")
        confidence = res.get("confidence")
        intent = res.get("intent", "")
        suggestion = res.get("suggestion", "")
    else:
        transcript = str(res)
        status = "ok"
        confidence = 1.0
        intent = ""
        suggestion = ""

    if transcript:
        log_voice_history(transcript, thread_id)

    return {
        "status": status,
        "transcript": transcript,
        "confidence": confidence,
        "intent": intent,
        "suggestion": suggestion,
        "demo_mode": False,
    }


@router.get("/voice/history")
async def get_voice_history():
    """Returns the last 20 voice history entries."""
    conn, engine = get_db_connection()
    try:
        if engine == "postgres":
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS voice_history "
                    "(id SERIAL PRIMARY KEY, transcript TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, thread_id TEXT)"
                )
                cur.execute(
                    "SELECT transcript, timestamp, thread_id FROM voice_history ORDER BY id DESC LIMIT 20"
                )
                rows = cur.fetchall()
                results = []
                for r in rows:
                    if isinstance(r, dict):
                        results.append({
                            "transcript": r.get("transcript", ""),
                            "timestamp": str(r.get("timestamp", "")),
                            "thread_id": r.get("thread_id", "")
                        })
                    else:
                        results.append({
                            "transcript": r[0],
                            "timestamp": str(r[1]),
                            "thread_id": r[2] if len(r) > 2 else ""
                        })
                return results
        else:
            cur = conn.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS voice_history "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, transcript TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, thread_id TEXT)"
            )
            cur.execute(
                "SELECT transcript, timestamp, thread_id FROM voice_history ORDER BY id DESC LIMIT 20"
            )
            rows = cur.fetchall()
            return [
                {
                    "transcript": r[0],
                    "timestamp": str(r[1]),
                    "thread_id": r[2]
                }
                for r in rows
            ]
    finally:
        conn.close()
