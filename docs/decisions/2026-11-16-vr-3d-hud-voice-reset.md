# Decision Log — 2026-11-16 — VR 3D HUD Voice + Reset Controls

## Session Type
[ ] Feature  [x] Bug fix  [ ] Refactor  [ ] Docs  [ ] Security

## What was built or changed
- Edit 1: Shortened shelf pillars from H=1.45 to H=0.87 so posts stop flush with the top shelf plank and never block floating UI.
- Edit 1: Renamed header banner "BAY A-14 · AISLE 3" → "Shelf", resized box to 0.72×0.18×0.02, raised to y=1.92 clear of the popup card zone.
- Edit 2: Added 3D WebGL HUD bar (hud3DGroup at pos 0,0.14,0.24, rot.x=-0.28) attached to shelfGroup, containing: live status canvas (update3DHudStatus), 🎤 Voice button (x=-0.21, hudAction="voice"), 🔄 Reset Demo button (x=0.21, hudAction="reset"), and set3DMicListening() helper. Moved spatialCardGroup onto shelfGroup. Added connectorLine (0x58a6ff, -0.39,1.07 → -0.39,1.24) from Widget-A up to the card.
- Edit 2: 3D Reset button label set to "🔄 Reset Demo" / "Restore Initial State"; matching 2D #btn-reset text changed to "🔄 Reset Demo".
- Edit 3: renderSpatialCard() now positions card at fixed local (-0.39, 1.50, 0.06) with zero rotation, showing card + connectorLine directly above Widget-A so Widget-A stays 100% unobstructed. Hide block also hides connectorLine.
- Edit 4: onXRSelect raycaster reordered → HUD buttons (Voice→btnMic.click(), Reset→resetDemo()) → spatial card buttons → Widget-A only (intersectObject(widgetAMesh,true), ignoring header/pillars/hud3DGroup).
- Edit 4: onXRFrame near-field poke extended to HUD buttons (<0.12m), card buttons (<0.13m), Widget-A (<0.15m) with index-finger-tip joint.
- Edit 4: setStatus(), showVoiceFeedback(), and recognition onstart/onend/onerror now sync with update3DHudStatus() and set3DMicListening().
- Edit 6: build3DShelf() now re-attaches hud3DGroup, spatialCardGroup, connectorLine via a typeof guard at the end, so clicking "🔄 Reset Demo" rebuilds bins without removing the 3D HUD bar or spatial card.

## Why (the problem being solved)
Meta Quest 2 immersive-ar mode does not render HTML dom-overlay, so all interactive controls (Voice, Reset, status) must live in WebGL. The 3D spatial card previously floated beside the shelf and could occlude Widget-A; pillars were too tall and blocked the popup zone; the 2D and 3D Reset buttons had inconsistent labels; and build3DShelf() wiped all shelfGroup children on reset, removing the HUD bar.

## Alternatives considered and rejected
| Option | Reason rejected |
|--------|----------------|
| Keep DOM overlay buttons for Voice/Reset | Not rendered by Quest 2 Browser in immersive-ar |
| Position spatial card beside shelf (prior behavior) | Occluded Widget-A, blocking pinch/poke |
| Attach HUD to scene instead of shelfGroup | Would not move with shelf when repositioned |
| No re-attach guard in build3DShelf() | Reset would destroy HUD bar and connector line |

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
- Verify Reset in AR preserves HUD bar + spatial card + connectorLine after build3DShelf() rebuild
- Confirm near-field poke distances (HUD <0.12m, card <0.13m, Widget-A <0.15m) feel right on Quest 2 hand tracking
- 13 pre-existing inline style= attributes could be cleaned as a separate refactor

## Call Stack Trace (post-edit)
```
Execution Call Stack Trace:
└── [Project] Browser / Meta Quest 2 immersive-ar WebXR session
    └── [Folder] frontend/vr/ → [File] index.html
        └── [Method] build3DShelf() → Edit 1 (pillars H=0.87, banner "Shelf" y=1.92) → Edit 6 (re-attach HUD/card/connector)
            └── [Method] onXRSelect() → Edit 4 (raycaster: HUD→card→Widget-A)
                ├── voice → btnMic.click() → recognition.start() → onstart→set3DMicListening(true)+update3DHudStatus(...,true)
                └── reset → resetDemo() → build3DShelf() → Edit 6 re-attach → HUD survives
            └── [Method] onXRFrame() → Edit 4 (near-field poke HUD<0.12m, card<0.13m, Widget-A<0.15m; pokeCooldownUntil=time+1200)
            └── [Method] setStatus() → Edit 4 (syncs update3DHudStatus(text,false))
            └── [Method] showVoiceFeedback() → Edit 4 (syncs update3DHudStatus(transcript→label,false))
            └── [Method] recognition events → Edit 4 (syncs set3DMicListening + update3DHudStatus)
```

## Verification
- `node --check` on extracted `<script>` — syntax OK
- Zero new inline `style=` attributes introduced by this session (13 pre-existing, noted above)
- `pytest tests/test_vr_voice_intent.py tests/test_s23_inventory.py -q` — 22 passed