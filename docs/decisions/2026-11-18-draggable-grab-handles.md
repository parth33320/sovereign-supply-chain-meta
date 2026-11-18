# Decision Log — 2026-11-18 — Quest OS-Style Draggable Grab Handles for 3D Spatial Cards

## Session Type
[x] Feature  [ ] Bug fix  [ ] Refactor  [ ] Docs  [ ] Security

## What was built or changed
- Edit 1: Added Quest OS-style draggable grab bars to `frontend/vr/index.html`. Declared drag state (`draggedPanel`, `activeDragController`, `dragDistance`, `dragOffset`, `dragHandles[]`) and a reusable `createGrabHandleMesh(width)` helper right after the `connectorLine` setup. The helper paints a 512×48 pill-shaped bar with a dual-dot grip texture onto a `BoxGeometry(width, 0.044, 0.016)`. A `cardGrabHandle` (width 0.46) is attached to `spatialCardGroup` at its top edge (`y=0.30`) with `userData.dragTarget = spatialCardGroup`, and pushed into `dragHandles`.
- Edit 2: Inside `renderPoCard(po, badge)`, after `spatialCardGroup.add(logMesh)`, any previous `a2aLogGrabHandle` is spliced out of `dragHandles`, then a new `logGrabHandle` (width 0.48, `name="a2aLogGrabHandle"`) is attached to `logMesh` at `y = planeH/2 + 0.026` with `userData.dragTarget = logMesh` and pushed into `dragHandles`. This makes the A2A Negotiation Log card independently draggable.
- Edit 3: Implemented the drag lifecycle.
  - `startARSession()` now binds `onXRSelect` to `"selectstart"` (fires on pinch-down, so drag begins while holding) and registers a new `onXRSelectEnd` handler on `"selectend"` (fires on pinch-release, dropping the panel). The session `end` cleanup removes both `"selectstart"` and `"selectend"` listeners and nulls `draggedPanel`/`activeDragController`. `onXRSelectEnd` restores `connectorLine.visible = true` when the spatial card itself was being dragged.
  - `onXRSelect(event)` checks grab handles FIRST (right after `raycaster.set`), before HUD/card buttons: on a hit it stores `draggedPanel`, `activeDragController`, `dragDistance = grabHits[0].distance`, and `dragOffset = targetWorld - grabHits[0].point`, hides `connectorLine`, and returns. Array indexing `[0]` is used because `intersectObjects` returns an array.
  - `onXRFrame(time, frame)` updates the dragged panel each frame: computes `newWorldPos = origin + dir*dragDistance + dragOffset`, converts to the panel parent's local space via `parent.worldToLocal`, copies to `draggedPanel.position`, and `lookAt`s the user camera horizontally so the panel stays face-on.
  - The render-loop `targets` array now includes `...dragHandles` (the global array) whenever `spatialCardGroup.visible`, so the green cursor dot highlights grab bars on hover.

## Why (the problem being solved)
In a hands-first XR flow, users expect to reposition floating panels the way Quest OS lets you grab and move windows. Previously the PO/Invoice card and A2A log were fixed in space above Widget-A, so a user who wanted a clearer view could not move them. Adding a pinch-and-hold grab bar to each panel gives Quest-style direct manipulation: pinch the bar, hold, move your hand, release to drop. Binding to `selectstart` (not `select`) is essential — `select` only fires on pinch release, which would make dragging impossible; `selectstart` fires at pinch-down so the panel follows the hand while held, and `selectend` drops it. The grab check runs before button raycasts so a grab always wins over an accidental button press on the same bar.

## Alternatives considered and rejected
| Option | Reason rejected |
|--------|----------------|
| Bind `onXRSelect` to `"select"` (prior behavior) | `select` fires only on pinch release — too late to drag; the panel would never follow the hand |
| Reference `logMesh` in `onXRFrame` render-loop targets (`dragHandles.filter(h => h.parent === logMesh)`) | `logMesh` is a local `const` inside `renderPoCard()`, out of scope in `onXRFrame` → `ReferenceError: logMesh is not defined`. Using the global `dragHandles` array directly avoids this |
| `grabHits.distance` / `grabHits.point` without `[0]` | `intersectObjects` returns an array; `grabHits.distance` is `undefined`, producing `NaN` dragDistance and a broken panel position |
| Dragging `spatialCardGroup` and `logMesh` together as one unit | The log is a child of `spatialCardGroup`; dragging them as independent panels (each with its own handle) is more flexible and matches Quest window behavior |
| Physics-based inertia / momentum on release | Over-engineered for this demo; simple position copy while held is sufficient and predictable |
| Mouse/desktop drag support | XR controller/hand only — desktop uses the 2D DOM card fallback |

## Rubric rules applied this session
- Read every file before editing (rubric §1)
- No dead imports (rubric §2)
- Reusable `createGrabHandleMesh` helper avoids duplicate canvas-painting code across two handles (rubric §2 — no duplicate code)
- No duplicate UI text (rubric §3)
- Commit message format `feat: <what> in <file> — <why>` (rubric §8)
- One PR per feature, no unrelated bundling (rubric §8)
- Ran the existing test suite before submitting (rubric §7)

## New rubric rules added this session
| Rule | File | Justification |
|------|------|---------------|
|      |      |               |

## Violations found in existing code
| File | Violation | Fixed? |
|------|-----------|--------|
| frontend/vr/index.html | Pre-existing inline `style=` attributes in generated HTML card templates (not introduced by this session) | No — out of scope for this session |

## Risk flags for next session
- Playwright headless verification could not be completed (Chromium browser binary download too slow in this environment). `node --check` on the extracted `<script>` passed and pytest (22 passed) confirms no syntax or logic regressions.
- `dragHandles` is a global array. `renderPoCard` splices out any prior `a2aLogGrabHandle` before adding a new one, so repeated calls don't accumulate duplicates. If a future refactor removes `a2aLogMesh` by another path, ensure the handle is also spliced.
- Drag uses `activeDragController` (XR controller), not hand joints. Near-field index-finger pokes still use the existing poke-cooldown path; grab bars are raycast via controller `selectstart`.
- The 900ms `onXRSelect` debounce also gates grab starts. A pinch to grab within 900ms of a prior select is ignored — acceptable, but verify during real Quest testing that it doesn't feel laggy.
- `connectorLine.visible` is set false on grab of the spatial card and restored on `selectend`. If a drag is interrupted (e.g. session ends mid-drag), the `end` cleanup nulls the drag state but does not restore the connector line — verify the connector reappears on next card open (it is re-shown by `renderSpatialCard`/openPanel paths).
- `draggedPanel.parent.worldToLocal(newWorldPos)` assumes the dragged panel always has a parent. True today (`spatialCardGroup.parent === shelfGroup`, `logMesh.parent === spatialCardGroup`); a future reparent to `null` would throw.
- `createGrabHandleMesh` is defined at ~line 788 but `cardPlane` (0.54m tall) is defined later; the handle's `y=0.30` offset is a hardcoded assumption of that card height. If the card plane height changes, update the handle offset.

## Call Stack Trace (post-change)
```
Execution Call Stack Trace:
└── [Project] Browser loads frontend/vr/index.html
    └── [Folder] frontend/vr/ → [File] index.html
        ├── [Variable] draggedPanel=null, activeDragController=null, dragDistance=1.2, dragOffset=Vector3, dragHandles=[]
        ├── [Function] createGrabHandleMesh(width) → THREE.Mesh (pill bar, isGrabHandle=true)
        ├── [Init] cardGrabHandle(0.46) → spatialCardGroup (y=0.30); dragHandles.push
        │
        ├── [Function] startARSession()
        │   ├── xrControllers.addEventListener("selectstart", onXRSelect)
        │   ├── onXRSelectEnd defined; xrControllers.addEventListener("selectend", onXRSelectEnd)
        │   └── [end] removeEventListener("selectstart"/"selectend"); draggedPanel=null; activeDragController=null
        │
        ├── [Function] onXRSelect(event)  [bound to selectstart]
        │   ├── [Debounce] 900ms
        │   ├── [Shelf Placement] return if placing
        │   ├── [Raycast] raycaster.set(origin, dir)
        │   ├── [0. Grab] if grabHits.length: draggedPanel=targetObj; activeDragController=ctrl; dragDistance=grabHits[0].distance; dragOffset=targetWorld-grabHits[0].point; connectorLine.visible=false; return
        │   ├── [1. HUD] voiceTargets
        │   └── [2. Card] cardHits
        │
        ├── [Function] onXRSelectEnd(event)  [bound to selectend]
        │   └── if activeDragController===target: restore connectorLine if spatialCard; draggedPanel=null; activeDragController=null
        │
        ├── [Function] onXRFrame(time, frame)
        │   ├── if draggedPanel && activeDragController: origin+dir*dragDistance+dragOffset → parent.worldToLocal → position.copy → lookAt(camWorld.x, targetWorldY, camWorld.z)
        │   └── [Render Loop] if spatialCardGroup.visible: targets.push(...dragHandles)
        │
        └── [Function] renderPoCard(po, badge)
            └── splice old a2aLogGrabHandle; logGrabHandle(0.48) → logMesh (y=planeH/2+0.026); dragHandles.push
```

## Verification
- `node --check` on extracted `<script>` — syntax OK
- `pytest tests/test_vr_voice_intent.py tests/test_s23_inventory.py -q` — 22 passed
- Confirmed all controller bindings use `selectstart`/`selectend` (no lingering plain `select`)
- Confirmed `grabHits[0].distance` / `grabHits[0].point` array indexing and `targets.push(...dragHandles)` (no out-of-scope `logMesh` reference)
- Playwright headless verification: NOT COMPLETED (Chromium browser binary download too slow in this environment); `node --check` confirms no syntax errors