# Architecture: SAM 3.1 Warehouse Image Analysis (S10)

## Fit
Integrates `warehouse_vision.py` into the Streamlit UI layer (`app.py`), bridging physical visual diagnostics with conversational task dispatching to `worker.py` and `graph.py` without touching `graph.py`.

## Endpoints
- Meta API `/chat/completions` (via `ChatOpenAI` and `META_API_BASE_URL`):
  - Primary model: `sam-3.1` (multimodal vision message)
  - Fallback model: `muse-spark-1.3` (multimodal vision message)

## Data
Visual analysis payload:
```json
{
  "items": [
    {
      "item": "Widget Alpha",
      "fill_level": 0.35,
      "status": "low"
    }
  ],
  "summary": "1 item detected, fill level at 35% (low stock)."
}
```

## Flow
1. User uploads image in `app.py` sidebar.
2. File size verified (<= 1MB).
3. `warehouse_vision.analyze_shelf_image(image_bytes)` encodes image as base64 data URI and invokes Meta API.
4. Extracted items and summary stored in `st.session_state.shelf_context`.
5. Visual metrics & summary rendered in sidebar.
6. When user submits voice or text command, `[VISUAL SHELF ANALYSIS: {summary}]\n{user_prompt}` is sent to `process_agent_task`.

## External
- `META_API_KEY`, `META_API_BASE_URL`, `META_MODEL_NAME`.
