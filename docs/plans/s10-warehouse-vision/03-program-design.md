# Program Design: SAM 3.1 Warehouse Image Analysis (S10)

## Files
- `warehouse_vision.py`: Vision processing module providing `analyze_shelf_image(image_bytes: bytes) -> Dict[str, Any]` and helper functions.
- `app.py`: Streamlit dashboard adding sidebar file uploader, size check, visual context persistence, and injection into chat / voice dispatch.
- `tests/test_warehouse_vision.py`: Unit tests (mocked OpenAI/ChatOpenAI) and live smoke test for `warehouse_vision.py`.
- `tests/test_warehouse_vision_ui.py`: UI integration tests validating file upload handling, file size rejection, and context injection into chat.

## Types & Signatures

```python
from typing import Dict, Any, List, Literal

ShelfItemStatus = Literal["low", "ok", "empty"]

class ShelfItem(TypedDict):
    item: str
    fill_level: float
    status: ShelfItemStatus

class ShelfAnalysisResult(TypedDict):
    items: List[ShelfItem]
    summary: str

def analyze_shelf_image(image_bytes: bytes) -> ShelfAnalysisResult: ...
```

## Call Stack
Execution Call Stack Trace:
└── [Project] Sovereign Supply Chain Dashboard
    ├── [Configuration/Env] META_API_KEY, META_API_BASE_URL, META_MODEL_NAME
    └── [Folder] root
        ├── [File] app.py
        │   └── [Method] st.sidebar.file_uploader("Upload Shelf Image")
        │       ├── [Variable State Shift] Inbound: uploaded_file.size <= 1_000_000
        │       └── [Method] warehouse_vision.analyze_shelf_image(image_bytes)
        └── [File] warehouse_vision.py
            └── [Method] analyze_shelf_image(image_bytes: bytes)
                ├── [Variable State Shift] b64_image = base64.b64encode(image_bytes).decode("utf-8")
                ├── [Method] ChatOpenAI(model="sam-3.1").invoke([HumanMessage(content=[...])])
                │   └── [Fallback on Exception] ChatOpenAI(model="muse-spark-1.3").invoke(...)
                ├── [Variable State Shift] Parsed JSON response -> {"items": [...], "summary": str}
                └── [Folder] app.py (return)
                    ├── [Variable State Shift] st.session_state.shelf_context = result
                    └── [Method] process_agent_task.delay(tenant_id, request_id, enriched_prompt)

## Test Plan
- `test_analyze_shelf_image_empty_bytes`: Asserts ValueError / handled error when empty image bytes are passed.
- `test_analyze_shelf_image_sam_success`: Tests successful call with model "sam-3.1".
- `test_analyze_shelf_image_sam_fallback_to_muse_spark`: Tests when "sam-3.1" errors (e.g. 404), falls back to "muse-spark-1.3".
- `test_analyze_shelf_image_invalid_json_recovery`: Tests handling of non-JSON LLM response.
- `test_analyze_shelf_image_live_smoke`: Runs against Meta API if `META_API_KEY` is present, skips if unset.
- `test_ui_file_size_rejection`: Asserts files > 1MB trigger error.
- `test_ui_context_injection`: Asserts `[VISUAL SHELF ANALYSIS: ...]` is prepended to dispatched prompt.

## Least Confident Decisions
- Whether Meta API `/chat/completions` currently registers `sam-3.1` or requires fallback to `muse-spark-1.3` (handled dynamically with try/except fallback).
