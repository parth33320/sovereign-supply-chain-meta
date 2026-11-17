# Status: AR Walk — Demo Improvements (Sovereign Supply Chain)

- Gate 1 — Product: APPROVED
- Gate 2 — Architecture: APPROVED
- Gate 3 — Program Design: APPROVED
- Gate 4 — Slice plan: APPROVED

## Slices
- [ ] Slice 1 — tracer bullet: Invoice tab locked on load + hover/focus tooltip + mic hover tooltip + "Listening..." gated on mic-active (no DB)
- [ ] Slice 2 — Invoice scene reframe: header, Verify & Release Payment / Flag Discrepancy, match confidence, dismissible dispute card, Pending supplier response state
- [ ] Slice 3 — backend GET /api/vr/inventory/demo + POST /api/vr/invoice-pay/demo; real Widget-A qty increment in mock_sap.db; shelf UI refresh from DB; completion toast + Reset button appears
- [ ] Slice 4 — Reset Demo button (top-right corner): restore Widget-A qty in DB, shelf back to default (not inbound), lock Invoice tab, clear approved PO/invoice state + voice history/transcript
- [ ] Slice 5 — removal & rejection: remove Guide button + disruption panel + "check disruptions" voice command; PO rejection = terminal state (no re-run loop)

## Notes for a fresh session
Target: `frontend/vr/index.html` + backend `vr_api.py` only. React `frontend/src/` dashboard untouched.
DB: SQLite `mock_sap.db` via `db.py`; Tenant_A Widget-A seeds at 50 units (`init_db.py:23`); real UPDATE via `vr_api.py`.
Voice commands in mic tooltip: restock Widget-A · approve · reject · check invoice · show shelf (disruption command removed).
PO rejection = terminal state ("PO rejected — Widget-A restock paused. Muse flagged for procurement review."); no re-run; judge hits Reset to retry approval.
Completion toast: "✅ Demo complete — Widget-A restocked. {newQty} units now in stock." shown ~3s, then Reset button (top-right corner) is the only way to rerun.
