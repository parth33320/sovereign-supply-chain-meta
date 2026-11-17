# VR Fix Plan: XR HUD Voice Tooltip (Workflow-State Driven)

## Problem

The voice tooltip currently only shows on:
- Mouse hover (2D mode only)
- Gaze hit on btn3DMic (rarely works — mesh is small, gaze precision poor)

The 3D HUD is the primary status display in XR and should always show the correct next-step voice command for the current workflow state.

## Solution

Call `update3DHudStatus(getVoiceTooltip())` at every workflow state change point. `setStatus()` already pipes to `update3DHudStatus`, so hook into existing state-change callsites.

Also remove the gaze-dependent tooltip logic from the cursor dot block (it conflicts — overwrites state-driven hints and resets HUD to "Supply Chain XR · Ready" mid-flow).

---

## Changes to `frontend/vr/index.html`

### Change 1 — After shelf placed, show first hint (2s delay)

**Find** (line ~568 in autoPlaceShelf, AND line ~662 in onXRSelect manual placement):
```javascript
setStatus("Shelf anchored on floor · Pinch or touch Widget-A");
```

**Replace BOTH occurrences with**:
```javascript
setStatus("Shelf anchored on floor · Pinch or touch Widget-A");
setTimeout(() => update3DHudStatus(getVoiceTooltip()), 2000);
```

### Change 2 — After restock negotiation completes (PO ready)

**Find** (line ~871, in triggerAgentRestock):
```javascript
setStatus('PO ready · Approve or reject', true);
```

**Add after it**:
```javascript
update3DHudStatus(getVoiceTooltip());
```

### Change 3 — After PO approved (approveAgentPO)

**Find** in `approveAgentPO` function, after `setStatus("PO approved · Tap Widget-A to validate invoice");` (line ~962):
```javascript
setStatus("PO approved · Tap Widget-A to validate invoice");
```

**Add after it**:
```javascript
update3DHudStatus(getVoiceTooltip());
```

### Change 4 — After invoice opened (onInvoicePinch)

**Find** in `onInvoicePinch` function, after `setStatus("Scanning invoice with Muse Image…");` (line ~1025):
```javascript
setStatus("Scanning invoice with Muse Image…");
```

**Add after it**:
```javascript
update3DHudStatus(getVoiceTooltip());
```

### Change 5 — On XR session start, initialize HUD with tooltip

**Find** in `startARSession` success callback (line ~644):
```javascript
setStatus("🥽 Starting XR…", true);
```

**Add after it**:
```javascript
setTimeout(() => update3DHudStatus(getVoiceTooltip()), 2500);
```

### Change 6 — After reset, show initial hint

**Find** in `resetDemo` function, after `setStatus("Demo reset · Ready");` (line ~1123):
```javascript
setStatus("Demo reset · Ready");
```

**Add after it**:
```javascript
update3DHudStatus(getVoiceTooltip());
```

### Change 7 — Remove gaze-dependent tooltip from cursor dot block

**Find** in cursor dot block (onXRFrame, lines ~753-760):
```javascript
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
```

**Replace With** (just the dot position, no HUD side-effect):
```javascript
        // gaze-based HUD update removed — tooltip driven by workflow state changes instead
        } else if (_prevHudHover) {
          _prevHudHover = false;
        }
```

**Note**: Leave `_prevHudHover` state variable (harmless) or remove if preferred.

---

## Validation Checklist

- [ ] HUD shows "Say: restock Widget-A..." after shelf placed (2s delay)
- [ ] HUD shows "Say: approve PO or reject PO" after restock negotiation
- [ ] HUD shows "Say: open invoice..." after PO approved
- [ ] HUD shows "Say: pay invoice..." after invoice opened
- [ ] HUD shows initial hint after XR session start (2.5s fallback)
- [ ] HUD shows restart hint after reset
- [ ] Gaze on mic button no longer overwrites/resets HUD
- [ ] Cursor dot still appears correctly on all targets

---

## Risk Mitigation

- All state-driven updates use existing `getVoiceTooltip()` which reads current workflow vars
- No new state variables needed
- Gaze tooltip removal eliminates conflict where HUD reset mid-flow
- Fallback timeout in Change 5 ensures HUD populated even if auto-place logic shifts

---

## Files to Modify

1. `frontend/vr/index.html` — 7 changes in the script block

---

## Out of Scope

- Changing `getVoiceTooltip()` logic (already correct)
- Adding visual indicator on 3D mic button itself
- Multi-language tooltips