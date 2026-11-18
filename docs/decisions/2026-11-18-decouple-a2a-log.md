# Decision Log — 2026-11-18 — Decouple A2A Negotiation Log from Purchase Order Card

## Session Type
[ ] Feature  [x] Bug fix  [ ] Refactor  [ ] Docs  [ ] Security

## What was built or changed
- Edit 1: In `renderPoCard(po, badge)` of `frontend/vr/index.html`, changed the stale-mesh cleanup lookup from `spatialCardGroup.getObjectByName("a2aLogMesh")` / `spatialCardGroup.remove(oldLog)` to `shelfGroup.getObjectByName("a2aLogMesh")` / `shelfGroup.remove(oldLog)`, matching the log's new parent.
- Edit 2: Changed the log mesh parenting and placement in `renderPoCard` from `logMesh.position.set(-0.82, 0.27 - planeH/2, 0.01); spatialCardGroup.add(logMesh);` to `logMesh.position.set(-1.21, 1.77 - planeH/2, 0.07); shelfGroup.add(logMesh);`. The A2A log is now a direct child of `shelfGroup` (a sibling of `spatialCardGroup`), positioned to the left of the PO card in shelf space.
- Edit 3: Extended `closePanel()` to also dispose and remove any `shelfGroup.getObjectByName("a2aLogMesh")` and splice its `a2aLogGrabHandle` out of `dragHandles`, so closing a panel fully tears down the independent log card.
- Edit 4: In `onXRSelect(event)`, changed the grab-handle gate from `if (spatialCardGroup.visible && dragHandles.length > 0)` to compute `const a2aLogVisible = shelfGroup.getObjectByName("a2aLogMesh")?.visible ?? false;` and gate on `if ((spatialCardGroup.visible || a2aLogVisible) && dragHandles.length > 0)`, so the log's grab bar stays draggable even when the PO card is closed/moved.
- Edit 5: In `onXRFrame`'s render-loop `targets` array, replaced the card-only block with `if (spatialCardGroup.visible) targets.push(cardBtnPrimary, cardBtnSecondary); const a2aLog = shelfGroup.getObjectByName("a2aLogMesh"); if (spatialCardGroup.visible || (a2aLog && a2aLog.visible)) targets.push(...dragHandles);` — pushing `dragHandles` once (never twice) whenever either the PO card or the log is visible, so the cursor-dot highlight works for both without duplicating the `a2aLogGrabHandle` entry.

## Why (the problem being solved)
The A2A Negotiation Log was a child of `spatialCardGroup` (the PO/Invoice card), so dragging the PO card dragged the log with it — the two panels could not be positioned independently. In a hands-first Quest flow users expect to move each floating panel on its own (Quest OS window behavior). Reparenting the log to `shelfGroup` (making it a sibling of the PO card) decouples the two drag targets. The visibility gates in `onXRSelect` and the render loop were updated so the log's grab bar remains interactive even when the PO card is hidden, and `closePanel` now cleans up the now-independent log mesh so it doesn't linger after the card closes.

## Alternatives considered and rejected
| Option | Reason rejected |
|--------|----------------|
| Keep log as child of `spatialCardGroup`, offset its local position on drag | Would require per-frame compensation math to counteract the parent's drag; fragile and couples the two panels' transforms |
| Make the log a child of `camera` (head-locked) | Head-locked panels are uncomfortable in XR and don't match the shelf-anchored spatial layout |
| Filter `dragHandles` per-parent in the render loop (`h.parent === a2aLog`) | `a2aLog` is a local lookup; simpler to push the whole `dragHandles` array once and rely on the handles being correct — avoids double-push and keeps the cursor highlight consistent |
| Leave stale `a2aLogGrabHandle` in `dragHandles` after close | Would raycast against a disposed/removed mesh; splicing it in `closePanel` prevents dangling references |

## Rubric rules applied this session
- Read every file before editing (rubric §1)
- No dead imports (rubric §2)
- No duplicate code — reused existing dispose/remove patterns (rubric §2)
- No duplicate UI text (rubric §3)
- Commit message format `fix: <what> in <file> — <why>` (rubric §8)
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
- Position `(-1.21, 1.77 - planeH/2, 0.07)` places the log to the left of the PO card in shelf space. Verify on-device that it doesn't overlap the shelf's left posts or clip at extreme head angles.
- `build3DShelf()` clears all `shelfGroup` children; if it runs while a log is present (e.g. reset), the log mesh is removed but the `a2aLogGrabHandle` entry in `dragHandles` is only cleaned by `closePanel`/`renderPoCard`. `resetDemo()` calls `closePanel()` first, so the handle is spliced — but a future direct `build3DShelf()` call without `closePanel` would leave a stale handle. Re-check if `build3DShelf` is ever called outside reset.
- The log is now always visible once added (child of `shelfGroup`, not gated by `spatialCardGroup.visible`). It hides only via `closePanel`. Confirm this matches the intended UX (log persists across PO-approve panel swaps).
- `shelfGroup.getObjectByName(...)` is recursive; no current name conflicts, but a future mesh named `a2aLogMesh` elsewhere would collide.

## Call Stack Trace (post-change)
```
Execution Call Stack Trace:
└── [Project] Browser loads frontend/vr/index.html
    └── [Folder] frontend/vr/ → [File] index.html
        ├── [Function] renderPoCard(po, badge)
        │   ├── [Variable] oldLog = shelfGroup.getObjectByName("a2aLogMesh") → shelfGroup.remove
        │   ├── [Variable State Shift] logMesh.parent: spatialCardGroup → shelfGroup
        │   ├── [Variable State Shift] logMesh.position: (-0.82, ...) → (-1.21, 1.77 - planeH/2, 0.07)
        │   └── [Method] shelfGroup.add(logMesh)
        │
        ├── [Function] closePanel()
        │   ├── [Method] shelfGroup.getObjectByName("a2aLogMesh") → dispose + shelfGroup.remove
        │   └── [Method] dragHandles.splice(a2aLogGrabHandle)
        │
        ├── [Function] onXRSelect(event)
        │   ├── [Variable] a2aLogVisible = shelfGroup.getObjectByName("a2aLogMesh")?.visible ?? false
        │   └── [Guard] if ((spatialCardGroup.visible || a2aLogVisible) && dragHandles.length) → grab
        │
        └── [Function] onXRFrame(time, frame)
            └── [Render Loop] if (spatialCardGroup.visible) push cardBtns; const a2aLog=...; if (spatialCardGroup.visible || (a2aLog && a2aLog.visible)) targets.push(...dragHandles)
```

## Verification
- `node --check` on extracted `<script>` — syntax OK
- `pytest tests/test_vr_voice_intent.py tests/test_s23_inventory.py -q` — 22 passed
- grep confirms all `a2aLogMesh` / `logMesh` references now use `shelfGroup` (no remaining `spatialCardGroup.add/remove/getObjectByName("a2aLogMesh")`)
- Playwright headless verification: NOT COMPLETED (Chromium browser binary download too slow in this environment); `node --check` confirms no syntax errors