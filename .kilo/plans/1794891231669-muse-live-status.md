# Muse Status Banner — Live Check Implementation Plan

## Goal
UI shows GREEN only when a live Meta Muse key works. Otherwise AMBER.

---

## Current State Analysis

### Backend (`backend/routers/vr.py`)
- `/vr/muse-status` endpoint currently returns `muse_active: true/false` based only on env var presence
- No live API call, no caching, no detailed state

### Frontend VR (`frontend/vr/index.html`)
- Banner at top of `#overlay` shows "Checking AI agent status…"
- Green if `muse_active: true`, amber otherwise
- Text is hardcoded in the fetch script

### Frontend React Components (hardcoded "Meta Muse" labels)
- `HITLCard.jsx:53` — "Meta Muse-Spark-1.3"
- `Analytics.jsx:118` — "Meta Muse-Spark-1.3"
- `Orchestrator.jsx:188, 189, 221, 243` — "Meta SAM 3.1", "muse-image-1.0", "Meta SAM 3.1", "Meta Muse Image 1.0"

### Main React App
- No status banner in header area (`App.jsx`, `Sidebar.jsx`)

### Tests
- `tests/test_meta_smoke.py` — basic smoke test, skips if no key

---

## Implementation Plan

### 1. Backend: `/vr/muse-status` Endpoint with Live Check + Caching

**File**: `backend/routers/vr.py`

**Changes**:
- Add in-memory cache with TTL (~5 minutes / 300 seconds)
- Replace `muse_status` function with logic:
  1. Check cache first
  2. If `DEMO_MODE == "1"` → return `{muse_active: false, state: "demo"}`
  3. If no `META_API_KEY`/`OPENAI_API_KEY` → return `{muse_active: false, state: "no_key"}`
  4. Else make ONE tiny live call via `get_llm()` with:
     - Prompt: "ping"
     - `max_tokens: 5`
     - `request_timeout: 10` (shorter than default 30s)
  5. On success → cache and return `{muse_active: true, state: "live", model: "muse-spark-1.3"}`
  6. On 401/403/auth error → cache and return `{muse_active: false, state: "invalid_key"}`
  7. On timeout/connection error → cache and return `{muse_active: false, state: "unreachable"}`
  8. On other exception → cache and return `{muse_active: false, state: "error"}`

**Cache structure**: `{ "data": {...}, "expires": timestamp }`

**Response format**: Always include `muse_active` (bool) and `state` (string). Never return the key or any part of it.

### 2. Frontend VR: Update Banner Logic + 3D XR Banner

**File**: `frontend/vr/index.html` (lines ~1563-1585)

**Changes**:
- Keep banner text exactly as-is (green/amber/catch branches unchanged)
- Change condition from `if (data.muse_active)` to `if (data.state === "live")` (in the fetch script at ~lines 1563-1585)
- All other states (including `demo`, `no_key`, `invalid_key`, `unreachable`, `error`) use amber branch
- Catch branch stays as-is
- **Fetch script update**: After setting the HTML banner, also call `updateMuseBanner3D(text, isLive)` with same text and colors for the 3D XR banner

**3D XR Banner (new)**:
- Add a 3D text panel in the Three.js scene, placed directly above the existing HUD panel (hdrPanel at y=1.92)
- The 3D panel should be a PlaneGeometry with CanvasTexture, similar to the existing HUD status panel
- Position: above the existing HUD panel (e.g., y ≈ 2.1 or slightly above hdrPanel)
- Same text and colors as the 2D banner (green branch / amber branch, unchanged)
- Update it from the same `muse-status` fetch result that drives the 2D banner
- Keep the 2D HTML banner at the top of the page
- Both 2D and 3D banners must show the same state at all times
- Implementation: reuse the same `update3DHudStatus` pattern but for a new "museBanner3DMesh" in the scene (placed after line 692: `const hud3DGroup = hdrPanel;`)
- **Variable naming**: Use consistent `museBanner3D*` prefix for all variables (canvas, ctx, tex, mesh, update function)
- **Canvas**: 1024×80, **PlaneGeometry**: 1.18×0.095, **Position**: y ≈ 0.27 (above hudStatusMesh at y=0.14)
- **Function**: `updateMuseBanner3D(text, isLive)` — draws rounded rect with green/amber colors, same text as 2D banner
- **Visibility management**:
  - The 3D muse banner mesh starts hidden (`mesh.visible = false`)
  - Set `mesh.visible = true` when an immersive XR session is active — this includes both real Quest 2 sessions and the Chrome XR Simulator (which fires `xrsessionstart` when "Enter XR" is clicked)
  - Set `mesh.visible = false` inside the `xrsessionend` event handler (when XR session ends)
  - The HTML banner always shows in 2D mode regardless of XR state
  - The condition to show the 3D panel is: an immersive XR session is active (`xrSession` is truthy), whether real Quest 2 or Chrome XR Simulator
- **Fetch script update** (lines ~1563-1585): After setting the HTML banner, also call `updateMuseBanner3D(text, isLive)` with same text and colors
- **XR session handlers**: Add `museBanner3DMesh.visible = true` in `xrsessionstart` handler; add `museBanner3DMesh.visible = false` in `xrsessionend` handler

**Status**: ✅ **IMPLEMENTED** — 3D banner attached to `hdrPanel` (survives `build3DShelf()`), canvas widened to 1024px, PlaneGeometry 1.18×0.095, position y=0.27, `updateMuseBanner3D()` with solid fill + stroke border, visibility tied to XR session lifecycle

### 3. Frontend React: Dynamic "Meta Muse" Labels

**Files to modify**:
1. `HITLCard.jsx` (line 53) — "Meta Muse-Spark-1.3"
2. `Analytics.jsx` (line 118) — "Meta Muse-Spark-1.3"
3. `Orchestrator.jsx` (lines 188, 189, 221, 243) — "Meta SAM 3.1", "muse-image-1.0", "Meta SAM 3.1", "Meta Muse Image 1.0"

**Approach**:
- Create a shared hook `useMuseStatus()` that fetches `/api/vr/muse-status` and provides `state` and `isLive` boolean
- Or pass status via context from a parent component that fetches once
- Replace hardcoded strings with conditional rendering:
  - If `isLive` → "Meta Muse-Spark-1.3" (green)
  - Else → "Demo Mode" (amber) or "Meta Muse (Demo)" (amber)

**Orchestrator.jsx `DEMO_PENDING_PO`**:
- Add a label like `(Demo)` when not live, or derive from status

### 4. Main React App: Add Status Banner to Header

**File**: `frontend/src/App.jsx` or `Sidebar.jsx`

**Approach**:
- Add a compact banner at top of main content area (below sidebar, above page content)
- Or add to Sidebar header area
- Use same `useMuseStatus()` hook
- Compact inline banner: `🟢 Live: muse-spark-1.3` / `🟡 Demo` / `🔴 Unreachable`

### 5. Tests (pytest)

**File**: `tests/test_muse_status.py` (new file)

**Test cases**:
| Scenario | Expected State |
|----------|----------------|
| No META_API_KEY env var | `no_key` |
| DEMO_MODE=1 | `demo` |
| get_llm raises 401/403 auth error | `invalid_key` |
| get_llm raises timeout/connection error | `unreachable` |
| Mocked successful "ping" response | `live` |
| Response never contains key string | assert |

**Implementation**:
- Use `monkeypatch` to set/unset env vars
- Use `unittest.mock.patch` on `llm_client.get_llm` to simulate responses/errors
- Test cache behavior (second call returns cached result)

### 6. Additional: Cache Invalidation on Config Change (Optional)

- If `META_API_KEY` changes at runtime, cache should invalidate
- Could add a `/vr/muse-status/refresh` POST endpoint to clear cache

---

## File Changes Summary

| File | Changes | Status |
|------|---------|--------|
| `backend/routers/vr.py` | Update `muse_status` with live check + cache; keep richer system prompt; import `get_llm` at module level for testability | ✅ Done |
| `frontend/vr/index.html` | Update banner condition to `data.state === "live"`; add 3D XR banner mesh (canvas 1024×80, PlaneGeometry 1.18×0.095, y≈0.27); `updateMuseBanner3D()` function; visibility management in XR session start/end; attached to `hdrPanel` (survives `build3DShelf()`) | ✅ Done |
| `frontend/src/components/HITLCard.jsx` | Dynamic label based on Muse status (`useMuseStatus` hook) | ✅ Done |
| `frontend/src/pages/Analytics.jsx` | Dynamic label (`useMuseStatus` hook) | ✅ Done |
| `frontend/src/pages/Orchestrator.jsx` | Dynamic labels + demo PO label (`useMuseStatus` hook) | ✅ Done |
| `frontend/src/App.jsx` | Add status banner to main content area (`useMuseStatus` hook) | ✅ Done |
| `frontend/src/hooks/useMuseStatus.js` (new) | Shared hook for fetching status + `museStatusLabel()` utility | ✅ Done |
| `tests/test_muse_status.py` (new) | 7 test cases: no_key, demo, invalid_key, unreachable, live_success, cache_behavior, key_leakage | ✅ Done |

---

## Risk Mitigation

- **Timeout handling**: 10s request_timeout + asyncio.wait_for wrapper as safety net
- **Cache stampede**: Simple in-memory dict with timestamp; acceptable for single-instance deployment
- **Key leakage**: Never log or return the key; error messages are generic
- **Backward compatibility**: VR banner text unchanged; only condition logic changes
- **Demo mode**: Explicitly handled before live check

---

## Validation Steps

1. **No key**: Set no env vars → amber banner, "no META_API_KEY set" (via state)
2. **DEMO_MODE=1**: → amber, state="demo"
3. **Invalid key**: `META_API_KEY=invalid123` → amber, state="invalid_key"
4. **Valid key**: Real working key → green, state="live"
5. **Cache**: Two rapid calls to `/vr/muse-status` → second returns cached
6. **React labels**: HITLCard, Analytics, Orchestrator show "Demo" when not live
7. **Main app banner**: Shows in header area
8. **Tests pass**: All 7 test cases pass
9. **3D XR banner**: In XR mode (real Quest 2 or Chrome XR Simulator), banner appears above HUD panel, mirrors 2D banner state exactly; hidden in 2D mode (mesh.visible=false until immersive session starts, then false again on session end) — ✅ **IMPLEMENTED** (attached to hdrPanel, survives build3DShelf(), canvas 1024px, PlaneGeometry 1.18×0.095)

---

## Implementation Order

1. Backend `/vr/muse-status` with cache + live check — ✅ **Done**
2. Frontend VR banner condition update + 3D XR banner mesh — ✅ **Done** (hdrPanel attachment, 1024px canvas, 1.18×0.095 geometry)
3. Shared `useMuseStatus` hook — ✅ **Done**
4. React component label updates (HITLCard, Analytics, Orchestrator) — ✅ **Done**
5. Main app status banner — ✅ **Done**
6. Tests — ✅ **Done** (7 tests passing)

---

## Out of Scope

- Changing `render.yaml` or committing secrets
- Multi-instance cache (Redis) — single instance in-memory is sufficient
- WebSocket push for real-time status changes
- Detailed model version in response beyond "muse-spark-1.3"