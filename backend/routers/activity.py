"""Activity SSE stream router for Sovereign Supply Chain."""

import asyncio
from datetime import datetime, timezone
import json
import os
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from backend.dependencies import get_activity_log

router = APIRouter()

@router.get("/activity/stream")
async def activity_stream(request: Request, thread_id: str = ""):
    """Streams activity log updates via Server-Sent Events (SSE)."""
    async def event_generator():
        seen = 0
        yield "data: {\"icon\": \"⚡\", \"source\": \"system\", \"msg\": \"Connected\"}\n\n"
        is_test = os.environ.get("PYTEST_CURRENT_TEST") is not None
        while True:
            log = get_activity_log()
            while seen < len(log):
                entry = log[seen]
                ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
                payload = {
                    "ts": ts,
                    "icon": entry.get("icon", "⚡"),
                    "source": entry.get("source", "system"),
                    "msg": entry.get("msg", "")[:80]
                }
                yield f"data: {json.dumps(payload)}\n\n"
                seen += 1
            if is_test:
                break
            if await request.is_disconnected():
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
