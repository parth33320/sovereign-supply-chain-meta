# Plan: AR Walk VR Demo UI Improvements

## Current State
`sovereign-supply-chain-meta/frontend/vr/index.html` is a single-file AR Walk demo served by `vr_api.py` (port 8502). The shelf scene (`ar-scene`) and invoice scene (`invoice-scene`) are toggled via `showScene()`. All popups render into `#ar-panel`, a full-width bottom slide-up sheet that blocks the shelf/invoice behind it.

## Decisions (resolved)
| # | Decision |
|---|----------|
| 1 | Remove the "📦 Shelf" nav button — shelf is always visible after entering AR; keep only "📄 Invoice" nav button |
| 2 | Add 3D CSS styling (perspective, translateZ/rotateX, depth shadows) to shelf bins for VR/AR look |
| 3 | Voice 'restock widget A' must render A2A negotiation log + PO approve/reject in the same floating popup as the shelf tap path |
| 4 | Widget-A pinch hint text → "👌 pinch to restock PO" (judge clarity) |
| 5 | Mic tooltip → position:fixed directly above the mic button (bottom-right), not top-left corner |
| 6 | Invoice locked tooltip text → "Supplier will send an invoice after you create a PO to restock Widget-A" |
| 7 | Shelf bin labels WGT-A..H → Widget-A..H for consistency |
| 8 | Invoice pinch text → "👌 Pinch for SAM to validate invoice with the PO" |
| 9 | All popups (A2A log, PO approve/reject, approved, rejected, invoice match/pay, discrepancy, payment released) → floating 3D cards positioned above shelf/invoice content; must NOT block the shelf or invoice behind them |
| 10 | Remove Widget-B pinch hint text + emoji (does nothing) |

## Ordered Tasks

### 1. Remove Shelf nav button
File: `frontend/vr/index.html`
- Delete the `<button class="nav-btn active" id="btn-shelf" ...>📦 Shelf</button>` element from `#nav-bar`
- Keep `#btn-invoice` (Invoice) button
- Update `showScene()` so it no longer references `btn-shelf` class toggling (or keep the reference harmless since element no longer exists — guard with null check)

### 2. Add 3D shelf styling
File: `frontend/vr/index.html`
- Add `perspective: 800px` to `.shelf-unit` or `.shelf-row`
- Add `transform: rotateX(15deg) translateZ(...)` style depth to `.bin` containers
- Add a 3D "bin face" look: gradient sides, `box-shadow` with offset, subtle `rotateY` per bin for parallax feel
- Keep existing fill bar / alert / label structure intact

### 3. Fix mic tooltip positioning
File: `frontend/vr/index.html`
- `#mic-tooltip` CSS: `position: fixed; top: auto; bottom: 90px; right: 20px;` (above mic button) — remove default top-left placement
- Add `left: auto` so it anchors to bottom-right near the mic button

### 4. Update invoice locked tooltip text
File: `frontend/vr/index.html`
- `#invoice-tooltip` text → "Supplier will send an invoice after you create a PO to restock Widget-A"

### 5. Update shelf labels WGT → Widget
File: `frontend/vr/index.html`
- `.bin-label` text: `WGT-A` → `Widget-A`, `WGT-B` → `Widget-B`, ... `WGT-H` → `Widget-H` (all 8 bins across both rows)

### 6. Update invoice pinch text
File: `frontend/vr/index.html`
- `.inv-pinch` span text: "👌 Pinch to extract &amp; review PO" → "👌 Pinch for SAM to validate invoice with the PO"

### 7. Update Widget-A pinch hint text
File: `frontend/vr/index.html`
- `#hint-a` text: "👌 pinch" → "👌 pinch to restock PO"

### 8. Remove Widget-B pinch hint
File: `frontend/vr/index.html`
- Delete the `<div class="bin-pinch-hint">👌 pinch</div>` under the Widget-B bin (Row 1, second bin)

### 9. Convert ar-panel bottom sheet to floating 3D popup cards
File: `frontend/vr/index.html`
- `#ar-panel` CSS: change from `position: fixed; bottom: 56px; left: 0; right: 0;` (full-width bottom sheet) to a floating card:
  - `position: fixed; top: 120px; left: 50%; transform: translateX(-50%);`
  - `width: auto; max-width: 420px;` (not full width)
  - `transform: perspective(900px) rotateX(8deg);` for 3D card feel
  - Heavy `box-shadow`, border, rounded corners, semi-transparent dark background
- Ensure `z-index` is above shelf/invoice (`z-index: 650`)
- The floating card appears above the shelf or invoice without covering them entirely (content remains visible behind/around)

### 10. Ensure voice 'restock widget A' shows A2A log + PO buttons
File: `frontend/vr/index.html`
- `handleVoiceCommand('restock ...')` already calls `showScene("shelf")` then `setTimeout(triggerAgentRestock, 300)` — verify `triggerAgentRestock()` renders into `#ar-panel` (floating card after task 9) and sets `panel.style.display = "block"`
- No logic change needed beyond task 9 restyling; the voice path already invokes the same renderer as the shelf-tap path

### 11. Validate on devtunnel
- Restart `uvicorn vr_api:app --port 8502` if not running
- Open `https://rh401wht-8502.use.devtunnels.ms/` in Chrome
- Confirm: Shelf button gone; shelf looks 3D; mic tooltip above mic emoji; invoice tooltip updated; WGT→Widget; Widget-A pinch hint updated; Widget-B pinch removed; A2A/PO popups are floating 3D cards above content; voice 'restock widget A' shows A2A log + approve/reject

## Open Questions / Out of Scope
- None — all items resolved above. Backend (`vr_api.py`) requires no changes for this round.

## Validation Criteria
- Reset button remains always visible top-right (from prior change)
- Shelf bin labels read Widget-A..H (not WGT..)
- Mic tooltip renders above mic button on hover
- Invoice locked tooltip reads the new supplier-invoice text
- Voice 'restock widget A' produces floating A2A log + PO approve/reject card above shelf
- Pinch-to-extract on invoice reads "Pinch for SAM to validate invoice with the PO"
- Widget-B bin has no pinch hint
- Popups do not cover the shelf or invoice underneath
