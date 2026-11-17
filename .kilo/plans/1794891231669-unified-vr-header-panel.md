# Unified VR Header Panel Implementation Plan

## Goal
Replace the static header sign + separate `hud3DGroup` with one unified header panel at the top of the shelf (y ≈ 1.92) containing:
- **Row 1**: Status text (dynamic, e.g. "Placing shelf…", "Tap Widget-A")
- **Row 2**: 🎤 Voice button | 🔄 Reset Demo button
- Both buttons must respond to pinch raycast and index-finger poke

## Current State Analysis

### Existing Components
1. **Header sign** (lines 257-261): Static mesh at `position.set(0, 1.92, 0)` with label "Shelf / Tap Widget-A to Restock"
2. **hud3DGroup** (lines 322-378): Separate group at `position.set(0, 0.14, 0.24)` with rotation `-0.28`, containing:
   - Status text canvas/mesh
   - Voice button (`btn3DMic`) with `userData.hudAction = "voice"`
   - Reset button (`btn3DReset`) with `userData.hudAction = "reset"`
   - `set3DMicListening()` function for mic state
3. **Re-attachment in build3DShelf** (lines 299-303): Re-adds `hud3DGroup` after shelf rebuild
4. **Raycast handling** (lines 571-578): Checks `btn3DMic` and `btn3DReset` for HUD interactions
5. **Poke handling** (lines 687-700): Checks index-finger distance to `btn3DMic` and `btn3DReset`
6. **Auto-place logic** (lines 659-664): Places shelf immediately on first XR frame
7. **Initial status** (line 639): "Point hand ray at floor · Pinch when blue ring appears"

## Required Changes

### Change 1: Replace Header Sign Creation in `build3DShelf` (lines 257-261)
**Find:**
```javascript
// Header sign raised high above the Widget-A popup zone
const hdrTex = createLabelTexture("Shelf","Tap Widget-A to Restock","#0d1117","#58a6ff");
const hdr = new THREE.Mesh(new THREE.BoxGeometry(0.72,0.18,0.02),
  new THREE.MeshBasicMaterial({map:hdrTex}));
hdr.position.set(0, 1.92, 0); shelfGroup.add(hdr);
```

**Replace with:**
```javascript
// Header panel: status text + Voice/Reset buttons (re-add from outer scope on rebuild)
if (typeof hdrPanel !== "undefined") {
  shelfGroup.add(hdrPanel);
}
```

### Change 2: Replace `hud3DGroup` Block with Unified `hdrPanel` (after `build3DShelf` definition, before line 322)
**Find:** Entire block from line 321 (`// ── 3D WebGL HUD Bar...`) through line 378 (`}` closing `set3DMicListening`)

**Replace with:**
```javascript
// ── Unified 3D Header Panel: Status + Voice + Reset (top of shelf, always visible in WebGL) ──
const hdrPanel = new THREE.Group();
hdrPanel.position.set(0, 1.92, 0);
shelfGroup.add(hdrPanel);

// Status text strip (top row)
const hudStatusCanvas = document.createElement("canvas");
hudStatusCanvas.width = 768; hudStatusCanvas.height = 80;
const hudStatusCtx = hudStatusCanvas.getContext("2d");
const hudStatusTex = new THREE.CanvasTexture(hudStatusCanvas);
const hudStatusMesh = new THREE.Mesh(
  new THREE.PlaneGeometry(0.84, 0.09),
  new THREE.MeshBasicMaterial({ map: hudStatusTex, transparent: true, side: THREE.DoubleSide })
);
hudStatusMesh.position.set(0, 0.14, 0.01);
hdrPanel.add(hudStatusMesh);

function update3DHudStatus(msg, isListening=false) {
  hudStatusCtx.clearRect(0, 0, 768, 80);
  hudStatusCtx.fillStyle = "rgba(13,17,23,0.85)";
  hudStatusCtx.beginPath();
  hudStatusCtx.roundRect(4, 4, 760, 72, 12);
  hudStatusCtx.fill();
  hudStatusCtx.fillStyle = isListening ? "#ff7b72" : "#e6edf3";
  hudStatusCtx.font = "600 26px sans-serif";
  hudStatusCtx.textAlign = "center";
  hudStatusCtx.fillText(String(msg || "Supply Chain AR · Ready").slice(0, 54), 384, 50);
  hudStatusTex.needsUpdate = true;
}
update3DHudStatus("Supply Chain AR · Ready");

// Button row (below status strip)
const btn3DMicTex = createLabelTexture("🎤 Voice", "Pinch or Poke", "#0d1117", "#58a6ff");
const btn3DMic = new THREE.Mesh(
  new THREE.BoxGeometry(0.38, 0.11, 0.025),
  new THREE.MeshBasicMaterial({ map: btn3DMicTex })
);
btn3DMic.position.set(-0.21, 0, 0.01);
btn3DMic.userData = { hudAction: "voice" };
hdrPanel.add(btn3DMic);

const btn3DResetTex = createLabelTexture("🔄 Reset Demo", "Restore Initial State", "#0d1117", "#8b949e");
const btn3DReset = new THREE.Mesh(
  new THREE.BoxGeometry(0.38, 0.11, 0.025),
  new THREE.MeshBasicMaterial({ map: btn3DResetTex })
);
btn3DReset.position.set(0.21, 0, 0.01);
btn3DReset.userData = { hudAction: "reset" };
hdrPanel.add(btn3DReset);

function set3DMicListening(active) {
  const tex = active
    ? createLabelTexture("⏹ Listening...", "Speak command", "#2a1215", "#f85149")
    : createLabelTexture("🎤 Voice", "Pinch or Poke", "#0d1117", "#58a6ff");
  btn3DMic.material.map.dispose();
  btn3DMic.material.map = tex;
  btn3DMic.material.needsUpdate = true;
}
// hud3DGroup alias so existing references keep working
const hud3DGroup = hdrPanel;
```

### Change 3: Fix `build3DShelf` Re-add Reference (lines 299-303)
**Find:**
```javascript
// Keep 3D HUD bar, spatial card, and connector line anchored to the shelf
// across Reset (build3DShelf clears shelfGroup.children on every rebuild)
if (typeof hud3DGroup !== "undefined") {
  shelfGroup.add(hud3DGroup, spatialCardGroup, connectorLine);
}
```

**Replace with:**
```javascript
// Re-attach header panel + spatial card + connector after shelf rebuild clears children
if (typeof hdrPanel !== "undefined") {
  shelfGroup.add(hdrPanel);
}
if (typeof spatialCardGroup !== "undefined") {
  shelfGroup.add(spatialCardGroup, connectorLine);
}
```

### Change 4: Apply Previous Fixes (Auto-place Delay + Status Message)

**4a. Update initial status message (line 639):**
```javascript
// Find:
setStatus("Point hand ray at floor · Pinch when blue ring appears", true);
// Replace:
setStatus("🥽 Starting AR…", true);
```

**4b. Add frame delay to auto-place (lines 659-664):**
```javascript
// Find:
function onXRFrame(time, frame) {
  if (!frame || !xrSession) return;
  // Auto-place shelf 1.35m in front of user at y=0 on first XR frame (no manual floor placement)
  if (!shelfPlaced) {
    autoPlaceShelf();
  }
// Replace:
let xrFrameCount = 0;
function onXRFrame(time, frame) {
  if (!frame || !xrSession) return;
  if (!shelfPlaced) {
    xrFrameCount++;
    if (xrFrameCount < 60) return;
    autoPlaceShelf();
  }
```

**4c. Reset frame counter on session end (line 631):**
```javascript
// Find:
hitTestSourceRequested = false; shelfPlaced = false;
// Replace:
hitTestSourceRequested = false; shelfPlaced = false; xrFrameCount = 0;
```

## Implementation Order

1. **Change 2** first (create new `hdrPanel` with all components) - establishes the new unified panel
2. **Change 1** (update `build3DShelf` to reference `hdrPanel`) 
3. **Change 3** (fix re-attachment logic in `build3DShelf`)
4. **Change 4** (apply auto-place delay and status message fixes)

## Validation Checklist

- [ ] Header panel appears at top of shelf (y ≈ 1.92) in WebGL
- [ ] Status text updates dynamically (shows "🥽 Starting AR…" on AR entry)
- [ ] Voice button (🎤) responds to pinch raycast → triggers `btnMic.click()`
- [ ] Reset button (🔄) responds to pinch raycast → triggers `resetDemo()`
- [ ] Voice button responds to index-finger poke (distance < 0.12)
- [ ] Reset button responds to index-finger poke (distance < 0.12)
- [ ] `set3DMicListening(true/false)` updates Voice button texture correctly
- [ ] `update3DHudStatus(msg, isListening)` renders status with rounded rect background
- [ ] Shelf rebuild (`build3DShelf`) preserves header panel, spatial card, connector line
- [ ] Auto-place waits ~60 frames (~1 second) before anchoring shelf
- [ ] Session end resets `xrFrameCount` to 0
- [ ] Old `hud3DGroup` references still work via alias (`const hud3DGroup = hdrPanel`)

## Risk Mitigation

- **Alias preservation**: `const hud3DGroup = hdrPanel` ensures existing raycast/poke code continues working without modification
- **Texture disposal**: `set3DMicListening` properly disposes old texture before assigning new one
- **Z-ordering**: Status mesh at `z=0.01`, buttons at `z=0.01` - both slightly forward of panel center to prevent z-fighting
- **Transparent status background**: `transparent: true` on status material with rounded rect drawing

## Files to Modify

- `frontend/vr/index.html` - Single file containing all VR logic

## Out of Scope

- DOM overlay status pill (lines 120-123) - remains unchanged
- 2D desktop fallback buttons (lines 142-143) - remain unchanged
- Spatial card system - remains unchanged
- Voice recognition logic - remains unchanged