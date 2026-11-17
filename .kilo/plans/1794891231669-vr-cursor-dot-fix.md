# VR Fix Plan: Green Cursor Dot Stuck on Widget-A

## Problem

The cursor dot raycaster uses `intersectObjects([...shelfGroup.children], true)` which recursively hits all shelf geometry. Widget-A box at y≈0.4 is geometrically closer to the camera than hdrPanel buttons at y=1.92, so Widget-A always wins and the dot gets stuck there regardless of where the ray points.

## Root Cause

In the cursor dot update block (onXRFrame), the targets array includes `...shelfGroup.children` with recursive=true. This causes the raycast to hit shelf planks/pillars/Widget-A before reaching the HUD buttons, even when the ray is pointing at the HUD buttons.

## Fix

Replace the cursor dot targets with an explicit allowlist — only the objects that should show the green dot. Remove the recursive `shelfGroup.children` spread entirely from the cursor dot block.

### File: `frontend/vr/index.html`

**Find** (cursor dot update block in onXRFrame, ~lines 740-760):

```javascript
    // Update pointer ray & cursor dot from primary active controller/hand
    cursorDot.visible = false;
    const activeCtrl = xrControllers.find(c => c.visible) || xrControllers[0];
    if (activeCtrl) {
      const { origin, dir } = getControllerRay(activeCtrl);
      raycaster.set(origin, dir);
      {
        const targets = [];
        // HUD buttons first (priority over shelf geometry)
        if (shelfGroup.visible) targets.push(btn3DMic, btn3DReset);
        if (spatialCardGroup.visible) targets.push(cardBtnPrimary, cardBtnSecondary);
        if (shelfGroup.visible) targets.push(...shelfGroup.children);
        const hits = raycaster.intersectObjects(targets, true);
        if (hits.length > 0) {
          cursorDot.visible = true;
          cursorDot.position.copy(hits[0].point);
          // Show voice tooltip in HUD when gazing at mic button
          const gazingAtMic = hits[0].object === btn3DMic;
          if (gazingAtMic && !_prevHudHover) {
            update3DHudStatus(getVoiceTooltip());
            _prevHudHover = true;
          } else if (!gazingAtMic && _prevHudHover) {
            update3DHudStatus("Supply Chain XR · Ready");
            _prevHudHover = false;
          }
        } else if (_prevHudHover) {
          // Cursor moved off all targets
          update3DHudStatus("Supply Chain XR · Ready");
          _prevHudHover = false;
        }
      }
    }
```

**Replace With**:

```javascript
    // Update pointer ray & cursor dot from primary active controller/hand
    cursorDot.visible = false;
    const activeCtrl = xrControllers.find(c => c.visible) || xrControllers[0];
    if (activeCtrl) {
      const { origin, dir } = getControllerRay(activeCtrl);
      raycaster.set(origin, dir);
      {
        // Explicit allowlist only — no recursive shelfGroup.children
        // (recursive hits shelf planks/pillars before HUD buttons and gets stuck)
        const targets = [];
        if (shelfGroup.visible) {
          targets.push(btn3DMic, btn3DReset);
          if (widgetAMesh) targets.push(widgetAMesh);
        }
        if (spatialCardGroup.visible) targets.push(cardBtnPrimary, cardBtnSecondary);
        const hits = raycaster.intersectObjects(targets, false);  // false = non-recursive, explicit list
        if (hits.length > 0) {
          cursorDot.visible = true;
          cursorDot.position.copy(hits[0].point);
          // Show voice tooltip in HUD when gazing at mic button
          const gazingAtMic = hits[0].object === btn3DMic;
          if (gazingAtMic && !_prevHudHover) {
            update3DHudStatus(getVoiceTooltip());
            _prevHudHover = true;
          } else if (!gazingAtMic && _prevHudHover) {
            update3DHudStatus("Supply Chain XR · Ready");
            _prevHudHover = false;
          }
        } else if (_prevHudHover) {
          update3DHudStatus("Supply Chain XR · Ready");
          _prevHudHover = false;
        }
      }
    }
```

## Key Changes

1. **Explicit allowlist only** — targets = `[btn3DMic, btn3DReset, widgetAMesh?, cardBtnPrimary?, cardBtnSecondary?]`
2. **No recursive shelfGroup.children** — removed `...shelfGroup.children` spread
3. **`intersectObjects(targets, false)`** — non-recursive since list is already flat
4. **HUD buttons first** — `btn3DMic`, `btn3DReset` listed before `widgetAMesh` so they win when ray hits them at their world position
5. **Widget-A still included** — `widgetAMesh` added explicitly so dot still appears when aiming at Widget-A box

## Validation

- [ ] Cursor dot appears on Voice button (🎤) when gazing at it
- [ ] Cursor dot appears on Reset button (🔄) when gazing at it
- [ ] Cursor dot appears on Widget-A when gazing at it
- [ ] Cursor dot appears on spatial card buttons when card is open
- [ ] Cursor dot does NOT get stuck on Widget-A when aiming at HUD buttons
- [ ] Voice tooltip HUD update still works on mic gaze
- [ ] HUD reverts to "Supply Chain XR · Ready" when cursor moves off all targets

## No Other Changes Needed

- The `onXRSelect` pinch handler has its own separate raycast that correctly hits shelf geometry — this fix only affects the cursor dot visual
- Spatial card, shelf interactions unchanged

## Risk Mitigation

- Conservative: explicit allowlist ensures only intended objects show cursor dot
- HUD buttons prioritized by array order
- Widget-A still interactive via explicit inclusion
- No regression on spatial card or pinch interactions