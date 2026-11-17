# Decision Log: 2026-11-17 — Quest 2 AR Fixes

## Context

Four root-cause bugs identified in `frontend/vr/index.html` Quest 2 `immersive-ar` passthrough:

1. **DOM Overlay invisible** — `#ar-panel-backdrop` lives inside `#overlay`; Meta Quest Browser does **not** render HTML `dom-overlay` inside `immersive-ar`; only WebGL renders
2. **Shelf placed too high** — `autoPlaceShelf()` uses `y=0` in `local-floor` which on Quest 2 without fresh floor calibration places shelf at chest/desk height (~0.8m). No user-adjustable height or floor-snap offset. Reticle hidden immediately in Quest 2 mode (`hitTestSupported === false`)
3. **No visible hands/rays** — `startARSession()` requests `hand-tracking` but Three.js scene never creates `renderer.xr.getHand(0/1)` or `renderer.xr.getController(0/1)` meshes/pointer lines
4. **Air-tap never hits Widget-A** — No visible laser ray/cursor dot; `onXRSelect()` doesn't check near-field index-finger proximity (`index-finger-tip` joint distance)

## Rubric Violations (before fix)

1. **§2 Code Quality**: No visible hands/rays means the UI is broken for the primary input method (hand tracking) — violates "every interactive feature must have clear user need"
2. **§3 UI Rules**: No cursor dot means no feedback for where the user is pointing — violates "minimal is better"
3. **§4 Error Handling**: No error handling for missing `dom-overlay` or `hand-tracking` — violates "every API call must have a try/except"
4. **§5 Security**: N/A (no user input)
5. **§6 Portability**: `hitTestSupported` fallback exists but doesn't cover Quest 2 floor-plane raycast — violates "all other dependencies must degrade gracefully"
6. **§7 Testing**: No test coverage for XR-specific behavior — violates "every new function needs at least one unit test"

## Decisions

- **Add 3D spatial card** (WebGL canvas texture) rendered beside the shelf in immersive mode, because Meta Quest Browser does not render HTML `dom-overlay` inside `immersive-ar`. The 2D DOM panel remains for desktop/mobile fallback.
- **Add visible Quest-style hands** (25 joint spheres per hand, thumb/index tips larger/green) and **pointer rays** (blue `THREE.Line`) so users can see their hands and aim in passthrough.
- **Add cursor dot** (green sphere) at raycast hit point for aim feedback.
- **Replace hit-test reticle** with **floor-plane raycast** (`THREE.Plane(0,1,0,0)`) for Quest 2 compatibility (works without `hitTestSupported`). Hit-test remains optional enhancement on supported devices.
- **Add near-field poke**: check `index-finger-tip` joint distance to `widgetAMesh` (< 0.14m) in `onXRFrame` for direct touch interaction (not pinch).
- **Keep existing 2D panel system** (`openPanel/closePanel`) and extend it to also call `renderSpatialCard(spec)` for 3D sync.
- **Pass `spatialSpec` objects** to all `openPanel` calls so the 3D card renders the same content as the 2D card.

## Call Stack Trace

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

## State Transitions

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

## Verification

- `node --check` on extracted `<script>` — syntax OK
- Zero inline `style=` attributes in generated HTML markup
- `pytest tests/test_vr_voice_intent.py -q` — 16 passed
- `pytest tests/test_s23_inventory.py -q` — pass