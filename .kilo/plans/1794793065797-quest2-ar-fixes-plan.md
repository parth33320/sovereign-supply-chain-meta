# Quest 2 AR Fixes — Implementation Plan

**Feature**: Fix Meta Quest 2 `immersive-ar` passthrough bugs in `frontend/vr/index.html`

**Last Decision**: 2026-11-16 — S26 VR Voice Intent + Demo Polish (from `docs/decisions/2026-11-16-s26-vr-voice-intent-polish.md`)

**Rubric Read**: Yes — `docs/CODING_RUBRIC.md` and `docs/decisions/2026-11-16-s26-vr-voice-intent-polish.md` reviewed.

---

## Problem Summary (from user analysis)

Four root-cause bugs in current Quest 2 `immersive-ar` implementation:

| # | Bug | Root Cause |
|---|-----|------------|
| 1 | DOM Overlay invisible | `#ar-panel-backdrop` lives inside `#overlay` — Meta Quest Browser does **not** render HTML `dom-overlay` inside `immersive-ar`; only WebGL renders |
| 2 | Shelf too high | `autoPlaceShelf()` uses `y=0` in `local-floor` which on Quest 2 without fresh floor calibration places shelf at chest/desk height (~0.8m). No user-adjustable height or floor-snap offset. Reticle hidden immediately in Quest 2 mode (`hitTestSupported === false`) |
| 3 | No visible hands/rays | `startARSession()` requests `hand-tracking` but Three.js scene never creates `renderer.xr.getHand(0/1)` or `renderer.xr.getController(0/1)` meshes/pointer lines |
| 4 | Air-tap never hits Widget-A | No visible laser ray/cursor dot; `onXRSelect()` doesn't check near-field index-finger proximity (`index-finger-tip` joint distance) |

---

## Solution Overview

Four coordinated edits to `frontend/vr/index.html` (single file, single `<script>` block):

| Edit | Scope | Purpose |
|------|-------|---------|
| **EDIT 1** | Core XR loop | Add 3D spatial card (WebGL), visible Quest-style hand joint meshes, pointer rays, cursor dot, floor-plane raycast reticle, near-field index-finger poke |
| **EDIT 2** | Panel system | Extend `openPanel/closePanel` to also render/update the 3D spatial card (`renderSpatialCard`) in sync with 2D DOM |
| **EDIT 3** | Action wiring | Pass `spatialSpec` object to `openPanel` in all workflow functions |
| **EDIT 4** | Specific call sites | Update each `openPanel` call with its `spatialSpec` payload |

All changes are **single-file, single-script-block** edits to `frontend/vr/index.html`.

---

## Vertical Slices (Tracer Bullets)

Following AGENTS.md Phase 3: build one thin end-to-end slice at a time, demoable at each step.

| Slice | Scope | Demo Goal | Tests |
|-------|-------|-----------|-------|
| **S1** | **Core XR: Hands + Rays + Reticle + Spatial Card** | Enter AR → see blue floor ring → pinch places shelf → see both hands (joint spheres), pointer rays, cursor dot → pinch Widget-A triggers `onShelfPinch` | `node --check`; manual Quest 2 / Chrome DevTools XR emulation |
| **S2** | **Spatial Card Sync** | Open/close panels → 3D card appears beside shelf with same content as 2D card → buttons on 3D card trigger same actions | Unit: `renderSpatialCard(spec)` → asserts `spatialCardGroup.visible`, `cardTex.needsUpdate` |
| **S3** | **Near-Field Poke** | Reach out and touch Widget-A with index finger (<14cm) → triggers `onShelfPinch` without pinch | Unit: distance check `< 0.14` → calls `onShelfPinch` |
| **S4** | **Wiring All Flows** | Every `openPanel` call includes `spatialSpec`; 3D card matches 2D content; buttons on 3D card fire same actions | Integration: `pytest tests/test_vr_voice_intent.py -q` (16 pass), `pytest tests/test_s23_inventory.py -q` |

Each slice is **independently demoable** and **reverts cleanly** on failure.

---

## Architectural Call Stack Trace

Following AGENTS.md §4.5 (6-tier resolution):

```
Execution Call Stack Trace:
└── [Project] Meta Quest 2 Browser → immersive-ar session
    ├── [Configuration/Env] META_API_KEY, META_BASE_URL, META_MODEL_NAME (from .env)
    └── [Folder] frontend/vr/
        └── [File] index.html (single-script module)
            ├── [Class] ThreeJS Scene Objects
            │   ├── shelfGroup (THREE.Group) — world-anchored shelf
            │   ├── spatialCardGroup (THREE.Group) — NEW: 3D WebGL card
            │   ├── xrControllers[2] (THREE.XRController) — NEW: pointer rays
            │   ├── xrHands[2] (THREE.XRHand) — NEW: joint spheres
            │   ├── cursorDot (THREE.Mesh) — NEW: target indicator
            │   └── reticle (THREE.Mesh) — floor ring
            ├── [Class] XR Session State
            │   ├── xrSession (XRSession)
            │   ├── xrRefSpace (XRReferenceSpace)
            │   ├── hitTestSource (XRHitTestSource)
            │   └── shelfPlaced (boolean)
            └── [Method] Runtime Operations
                ├── startARSession() → requests immersive-ar, sets up hands/controllers
                ├── onXRFrame(time, frame) → per-frame loop
                │   ├── Updates hand joint meshes from hand.joints
                │   ├── Checks near-field poke (index-finger-tip distance < 0.14m)
                │   ├── Raycasts pointer ray → cursorDot, spatialCard buttons, shelf
                │   └── Projects ray onto floorPlane (y=0) for reticle
                ├── onXRSelect(event) → pinch/air-tap handler
                │   ├── If !shelfPlaced: anchors shelf at reticle (y=0)
                │   ├── Else: raycasts against spatialCardGroup + shelfGroup
                │   └── Near-field handled in onXRFrame (not select)
                ├── autoPlaceShelf() → fallback for Quest 2 (no hit-test)
                │   └── Places shelf 1.35m ahead at y=0, lookAt camera
                ├── renderSpatialCard(spec) → draws 2D canvas → CanvasTexture → cardPlane
                │   ├── Updates cardBtnPrimary/Secondary hitboxes + userData.action
                │   └── Positions spatialCardGroup beside shelfGroup
                ├── openPanel(html, accent, spatialSpec) → 2D DOM + 3D spatial card
                └── closePanel() → hides both DOM and spatialCardGroup
```

**State Mutability / Variable Transitions**:

| Variable | Initial | After `startARSession` | After `onXRSelect` (place) | After `onXRSelect` (interact) | After `closePanel` |
|----------|---------|------------------------|----------------------------|-------------------------------|---------------------|
| `xrSession` | `null` | `XRSession` | — | — | `null` |
| `xrRefSpace` | `null` | `XRReferenceSpace` | — | — | `null` |
| `hitTestSource` | `null` | `XRHitTestSource` | — | — | `null` |
| `shelfPlaced` | `false` | `false` | `true` | — | `false` |
| `shelfGroup.visible` | `false` | `false` | `true` | — | `false` |
| `spatialCardGroup.visible` | `false` | `false` | — | `true` (on panel open) | `false` |
| `cursorDot.visible` | `false` | `false` | — | `true` (on hit) | `false` |
| `pokeCooldownUntil` | `0` | `0` | — | `time + 1200` (on poke) | `0` |

---

## Detailed Edit Specifications

### EDIT 1: Core XR Loop (lines ~317–496)

**FIND**: Current `onXRSelect`, `startARSession`, `autoPlaceShelf`, `onXRFrame` (lines 327–496)

**REPLACE WITH**: New implementation adding:
- `spatialCardGroup` + `cardCanvas` + `cardCtx` + `cardTex` + `cardPlane`
- Interactive 3D hitboxes: `cardBtnPrimary`, `cardBtnSecondary`
- `xrControllers[2]` from `renderer.xr.getController(0/1)` with pointer ray `THREE.Line`
- `xrHands[2]` from `renderer.xr.getHand(0/1)` with 25 joint spheres each (thumb/index tips larger/green)
- `cursorDot` (green sphere) for raycast hit point
- `floorPlane = new THREE.Plane(0,1,0,0)` for Guardian floor raycast
- `getControllerRay(ctrl)` helper extracting origin/direction from controller matrix
- `handleSpatialCardHit(hitObj)` routing primary/secondary button actions
- `onXRSelect` → checks spatial card buttons first, then shelf, delegates near-field to frame loop
- `startARSession` → sets up `xrControllers`, `xrHands`, adds `select` listeners to controllers
- `autoPlaceShelf` → 1.35m ahead at `y=0`, `lookAt` camera
- `onXRFrame` → per-frame:
  - Pulse Widget-A emissive
  - Update all 25 joint spheres per hand from `hand.joints`; **near-field poke**: if `jointName === "index-finger-tip"` and distance to `widgetAMesh` < 0.14m and `time > pokeCooldownUntil` → `onShelfPinch()`
  - Raycast from primary controller/hand → `cursorDot` at hit point; if `!shelfPlaced` project onto `floorPlane` for reticle; else check spatial card buttons + shelf

**Key Behavioral Changes**:
- Reticle now uses **floor-plane raycast** (works on Quest 2 without hit-test) instead of hit-test source
- Near-field poke handled in **frame loop** (continuous), not `select` event
- Spatial card renders **alongside** 2D panel — visible in Quest 2 passthrough
- Hand joints + pointer rays **always visible** in immersive session

---

### EDIT 2: Panel System Sync (lines ~536–547)

**FIND**: Current `openPanel(html, accent)` and `closePanel()`

**REPLACE WITH**:
```javascript
function openPanel(html, accent="accent", spatialSpec=null) {
  arPanel.innerHTML = `<div class="card card--${accent}">${html}</div>`;
  panelBD.classList.add("open");
  arPanel.querySelectorAll("button").forEach(btn =>
    btn.addEventListener("beforexrselect", ev => ev.preventDefault()));
  renderSpatialCard(spatialSpec);  // NEW: sync 3D card
}
function closePanel() {
  panelBD.classList.remove("open");
  renderSpatialCard(null);  // NEW: hide 3D card
}
```

---

### EDIT 3 & 4: Wire All Action Functions (lines ~574–734)

**FIND/REPLACE** each `openPanel` call to include `spatialSpec` object matching the 2D card content:

| Function | `spatialSpec` Fields |
|----------|---------------------|
| `triggerAgentRestock` | `{title:"🤖 A2A Procurement", badge:"SAM · muse-spark-1.3", accent:"accent", lines:[{text:"Widget-A: 0 units — stockout detected",color:"#f85149",bold:true},{text:"Broadcasting RFQ to 3 suppliers..."},{text:"Evaluating cost, lead time & reliability..."}]}` |
| `renderPoCard` | `{title:"⏸ Purchase Order Approval", badge:po.po_id||"PO-2026-847", accent:"warn", lines:[{text:`Winner: ${po.supplier} (Best Score)`,color:"#3fb950",bold:true},{text:`Item: ${po.sku} × ${po.qty} units`},{text:`Unit Price: $${Number(po.unit_price).toFixed(2)} · Delivery: ${po.delivery_days} days`},{text:`Total Cost: $${Number(po.total).toLocaleString()}`,color:"#58a6ff",bold:true},{text:"Pinch Approve PO below to authorize:",color:"#8b949e"}], primaryLabel:"✅ Approve PO", primaryColor:"#238636", primaryAction:approveAgentPO, secondaryLabel:"✗ Reject", secondaryColor:"#da3633", secondaryAction:rejectAgentPO}` |
| `approveAgentPO` | `{title:"✅ PO Approved", badge:"AWAITING INVOICE", accent:"ok", lines:[{text:`Locked with ${approvedPO.supplier} — 500× Widget-A`,bold:true},{text:"Widget-A awaits invoice verification.",color:"#d29922"},{text:"Pinch Validate Invoice or Widget-A next.",color:"#58a6ff"}], primaryLabel:"🧾 Validate Invoice", primaryColor:"#1f6feb", primaryAction:onInvoicePinch, secondaryLabel:"Close", secondaryColor:"#30363d", secondaryAction:closePanel}` |
| `onInvoicePinch` | `{title:"🧾 Invoice INV-2026-847", badge:"muse-image-1.0", accent:"accent", lines:[{text:`Vendor: ${activeInvoice.supplier}`,bold:true},{text:"Item: 500× Widget-A @ $8.20"},{text:`Total: ${activeInvoice.total} · PO Match: 100%`,color:"#3fb950",bold:true}], primaryLabel:"💳 Verify & Pay", primaryColor:"#238636", primaryAction:verifyInvoicePayment, secondaryLabel:"Close", secondaryColor:"#30363d", secondaryAction:closePanel}` |
| `verifyInvoicePayment` | `{title:"💸 Payment Released", badge:"COMPLETE", accent:"ok", lines:[{text:"✅ 3-way match: PO ↔ Invoice ↔ GRN verified",color:"#3fb950",bold:true},{text:"PO-2026-847 · Apex Logistics · $4,100.00"},{text:`📦 Widget-A Stock Updated: ${newQty} units`,color:"#3fb950",bold:true}], primaryLabel:"Done", primaryColor:"#238636", primaryAction:closePanel}` |

---

## Validation Checklist (per CODING_RUBRIC.md & Decision Log)

| Check | Tool/Command | Expected |
|-------|--------------|----------|
| Syntax | `node --check` on extracted `<script>` | Syntax OK |
| No inline `style=` in generated HTML | HTML parser / manual grep | Zero occurrences |
| VR Voice Intent tests | `pytest tests/test_vr_voice_intent.py -q` | 16 passed |
| Inventory tests | `pytest tests/test_s23_inventory.py -q` | Pass |
| Voice handler tests | `pytest tests/test_voice_handler.py -q` | Pass (pre-existing failures documented) |
| Manual XR emulation | Chrome DevTools → Sensors → XR → "Meta Quest 2" | Hands visible, rays, reticle, spatial card, poke works |
| No new inline `style=` | `grep -n 'style=' frontend/vr/index.html` | Only in `<style>` block |
| Decision log created | `docs/decisions/YYYY-MM-DD-quest2-ar-fixes.md` | File exists with rubric violations, decisions, verification |

---

## Risk Assessment & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `renderer.xr.getHand()` not available on older Three.js (r128) | Low | High | Three.js r128 (used in CDN) supports `renderer.xr.getHand()`; verify at runtime |
| `hand.joints` iteration order unstable | Low | Medium | Use explicit joint name check (`index-finger-tip`) not index |
| `domOverlay` root `#overlay` conflicts with 3D card | Medium | Low | 3D card is separate WebGL mesh; DOM overlay still used for 2D HUD (status, mic, reset) |
| Near-field poke false positives | Low | Medium | Cooldown 1200ms; distance threshold 0.14m; requires `shelfPlaced && shelfGroup.visible` |
| Quest 2 hit-test fallback breaks on future OS updates | Low | Low | Floor-plane raycast is primary; hit-test only enhances reticle on supported devices |
| Spatial card button hitboxes misaligned | Low | Medium | Buttons positioned relative to `cardPlane` geometry; `raycaster.intersectObjects([btnPrimary, btnSecondary])` uses exact mesh bounds |

---

## Out of Scope

- Backend API changes (`vr_api.py`, database) — **unchanged**
- Voice intent endpoint (`/api/vr/interpret-voice`) — **unchanged**
- Desktop 2D fallback UI — **unchanged** (still works via `#ar-scene`)
- Existing tests — **must continue passing**; no test modifications
- New test files — **not required** (existing suite covers behavior)

---

## Open Questions (need user confirmation)

1. **Three.js version lock**: Current CDN uses `r128`. Confirm we stay on r128 (supports `getHand()`, `getController()`). If upgrading to r150+, import paths change.

2. **Spatial card button actions**: The `primaryAction`/`secondaryAction` are function references (e.g., `approveAgentPO`). Confirm this pattern is acceptable vs. string action names.

3. **Poke threshold**: 0.14m (14cm) for index-finger-tip → Widget-A. Confirm distance; Quest 2 hand tracking jitter may need 0.16m.

4. **Spatial card position**: Currently placed `0.92m` to the right of shelf, `1.15m` height. Confirm ergonomics for seated/standing users.

5. **Cursor dot visibility**: Green sphere at ray hit point. Confirm color/size (0.016m radius) is visible in passthrough.

---

## Next Steps

If the above is approved, I will:
1. Create decision log `docs/decisions/2026-11-17-quest2-ar-fixes.md` with rubric violations & decisions
2. Execute slices S1–S4 sequentially with verification at each step
3. Run full test suite and create final decision log
4. Push to `main`

**Please confirm or adjust the open questions above.**