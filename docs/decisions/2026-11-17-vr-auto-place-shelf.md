# Decision Log — 2026-11-17 — VR Auto-Place Shelf on AR Start

## Session Type
[ ] Feature  [x] Bug fix  [ ] Refactor  [ ] Docs  [ ] Security

## What was built or changed
- Edit A: `onXRFrame(time, frame)` now calls `autoPlaceShelf()` on the very first XR frame when `!shelfPlaced`, so the shelf spawns automatically `1.35m` in front of the camera at `y=0`, facing the user — removing the manual blue-ring floor-placement / pinch-to-place step for judges.
- Edit B: Removed the `if (!shelfPlaced)` floor-reticle projection branch inside `onXRFrame`. `reticle` now stays hidden; `cursorDot` immediately highlights `Widget-A` and the 3D HUD/card buttons on the targets raycast block (runs unconditionally every frame).
- Edit C: `resetDemo()` now sets `shelfPlaced = false` when `xrSession` is active, so `onXRFrame` re-anchors the shelf `1.35m` in front of the user's current position on the next frame after a Reset.

## Why (the problem being solved)
Judges launching immersive-ar on Quest 2 had to manually aim the blue floor ring and pinch to place the shelf before any interaction was possible. With dom-overlay not rendered in immersive-ar, there is no HTML fallback to place the shelf, so the shelf must appear automatically in front of the user on session start. Reset also needed to re-anchor the shelf relative to the user's new head position.

## Alternatives considered and rejected
| Option | Reason rejected |
|--------|----------------|
| Keep manual floor-ring pinch-to-place | Requires an extra user step before any demo interaction; fragile on Quest 2 without fresh floor calibration |
| Place shelf in `startARSession()` directly | Camera pose isn't fully established at session-request time; first XR frame is the reliable anchor point |
| Keep reticle visible after auto-place | Adds visual clutter; cursorDot on targets already provides aim feedback |

## Rubric rules applied this session
- Read every file before editing (rubric §1)
- Commit message format `feat|fix: <what> in <file> — <why>` (rubric §8)
- One PR per feature, no unrelated bundling (rubric §8)

## New rubric rules added this session
| Rule | File | Justification |
|------|------|---------------|
|      |      |               |

## Violations found in existing code
| File | Violation | Fixed? |
|------|-----------|--------|
| frontend/vr/index.html | 13 inline `style=` attributes in generated HTML (pre-existing, not introduced by this session) | No — out of scope for this session |

## Risk flags for next session
- `floorPlane` (module-level const) is no longer referenced after removing the floor-reticle branch — harmless but could be removed in a cleanup
- Verify auto-placed shelf doesn't collide with real-world furniture behind the user on Quest 2 (1.35m is a conservative distance)

## Call Stack Trace (post-edit)
```
Execution Call Stack Trace:
└── [Project] Browser / Meta Quest 2 immersive-ar WebXR session
    └── [Folder] frontend/vr/ → [File] index.html
        └── [Method] startARSession() → renderer.setAnimationLoop(onXRFrame)
            └── [Method] onXRFrame(time, frame) → Edit A (autoPlaceShelf if !shelfPlaced) → Edit B (unconditional raycast targets; reticle hidden; cursorDot on Widget-A/3D buttons)
                └── [Method] autoPlaceShelf() → shelfGroup 1.35m ahead at y=0, lookAt camera, shelfPlaced=true
                    └── [Variable State Shift] shelfPlaced: false → true; shelfGroup.visible: false → true
            └── [Method] onXRSelect(event) → pinch on Widget-A / HUD buttons / card buttons
            └── [Method] resetDemo() → Edit C (if xrSession: shelfPlaced=false) → closePanel() → fetch /api/vr/reset-demo → build3DShelf() → setStatus("Demo reset · Ready")
                └── [Variable State Shift] shelfPlaced: true → false (when xrSession active)
                └── [Method] onXRFrame (next frame) → Edit A → autoPlaceShelf() → shelf re-anchored 1.35m ahead of current camera pose
                    └── [Variable State Shift] shelfPlaced: false → true
```

## Verification
- `node --check` on extracted `<script>` — syntax OK
- Zero new inline `style=` attributes (13 pre-existing, noted above)
- `pytest tests/test_vr_voice_intent.py tests/test_s23_inventory.py -q` — 22 passed