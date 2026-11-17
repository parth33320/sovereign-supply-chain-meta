# Decision Log: 2026-11-17 — Add Diagnostic Fields to /api/vr/muse-status

## Context

The `/api/vr/muse-status` endpoint in `backend/routers/vr.py` was returning minimal status information. When the Muse API connectivity fails, operators need diagnostic details to troubleshoot without exposing the API key.

## Rubric Check

- **§2 Code Quality**: No dead imports, no duplicate code
- **§4 Error Handling**: Every API call has try/except with user-friendly error message; auth errors show "check your API key" not raw 401
- **§5 Security**: Never log API keys, user prompts, or PII to console or files — diagnostic fields explicitly exclude the key value
- **§6 Portability**: App must run with ONLY META_API_KEY set as env var; DEMO_MODE=1 works with zero other env vars
- **§7 Testing**: Tests updated and passing

## Changes

### Backend (`backend/routers/vr.py`)

Updated `/api/vr/muse-status` endpoint to return diagnostic fields in all responses:

**Success response now includes:**
- `"muse_active": true`
- `"state": "live"`
- `"model": "muse-spark-1.3"`
- `"demo_mode": os.environ.get("DEMO_MODE")` — boolean string
- `"has_key": bool(api_key)` — whether any key is configured
- `"key_len": len(api_key) if api_key else 0` — length only, never the key itself
- `"base_url": base_url` — the Meta API base URL being used

**Error responses now include:**
- `"muse_active": false`
- `"state": "invalid_key" | "unreachable" | "error"` — classified error state
- `"demo_mode": os.environ.get("DEMO_MODE")`
- `"has_key": bool(api_key)`
- `"key_len": len(api_key) if api_key else 0`
- `"base_url": base_url`
- `"http_status": <int>` — HTTP status code from upstream (when available)
- `"detail": "<first 300 chars of response>"` — truncated error detail from Meta API

**Cache invalidation:** Both success and error responses include `key_hash` for cache invalidation when `META_API_KEY` changes.

**Security:** The API key value is never exposed — only presence (`has_key`) and length (`key_len`) are returned.

### Tests

All 7 existing tests in `tests/test_muse_status.py` pass. Tests mock `langchain_openai.ChatOpenAI` at the class level to simulate various error conditions.

## Verification

- `pytest tests/test_muse_status.py -v` — 7 passed
- `pytest tests/test_vr_voice_intent.py -q` — 18 passed
- `pytest tests/test_s23_inventory.py -q` — 4 passed

## Call Stack Trace

```
Execution Call Stack Trace:
└── [Project] FastAPI backend → /api/vr/muse-status
    ├── [Configuration/Env] META_API_KEY, META_API_BASE_URL, META_MODEL_NAME, DEMO_MODE
    ├── [Folder] backend/routers/
    │   └── [File] vr.py
    │       ├── [Function] muse_status()
    │       │   ├── [Cache] _muse_cache check with key_hash invalidation
    │       │   ├── [Check] DEMO_MODE → return demo state
    │       │   ├── [Check] META_API_KEY/OPENAI_API_KEY presence
    │       │   ├── [Live Check] ChatOpenAI(ping) with fresh instance
    │       │   │   ├── Success → return live state + diagnostic fields
    │       │   │   └── Exception → classify error + diagnostic fields
    │       │   └── [Cache] Update _muse_cache with key_hash
    │       └── [Function] muse_status_refresh() — clears cache
```

## Verification

- [x] `node --check` on extracted `<script>` from `frontend/vr/index.html` — syntax OK
- [x] `pytest tests/test_muse_status.py -v` — 7 passed
- [x] `pytest tests/test_vr_voice_intent.py -q` — 18 passed
- [x] `pytest tests/test_s23_inventory.py -q` — 4 passed

## Files Modified

- `backend/routers/vr.py` — Updated `muse_status()` endpoint with diagnostic fields
- `docs/decisions/2026-11-17-muse-status-diagnostics.md` — This decision log