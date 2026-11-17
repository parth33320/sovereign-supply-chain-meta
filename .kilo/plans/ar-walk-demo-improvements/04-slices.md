# Slices: AR Walk — Demo Improvements

Ordered vertical slices. Slice 1 is the tracer bullet (end-to-end, demoable without DB).

## Slice 1 — Tracer bullet: nav lock + mic tooltip + Listening gate (no DB)
- Grey Invoice tab on load; add hover/focus tooltip "Complete voice or pinch restock to generate a supplier invoice".
- Replace Guide button in bottom nav (nav = Shelf | Invoice).
- Add mic hover/focus tooltip card listing voice commands; dismiss on mouse-out / tap-away.
- Gate "Listening..." on `micActive` flag (only while recording).
- Verify: open `frontend/vr/index.html` against running `vr_api`; Invoice locked, tooltip shows, mic tooltip shows, Listening only during recording.

## Slice 2 — Invoice scene reframe
- Header: "⚠️ Invoice received for PO #2026-847 — verify amounts match and release payment".
- Replace Approve/Reject with "Verify & Release Payment" / "Flag Discrepancy".
- On invoice scan: cross-check extraction vs `approvedPO`; surface match confidence + delta; no-API-key fallback "✅ All fields match PO #2026-847".
- Flag Discrepancy: dismissible dispute-draft card ("Invoice shows $8.50/unit; PO locked $8.20/unit — requesting credit memo for $150 difference"), "Pending supplier response" state, production note; no re-negotiate language.
- Verify & Release Payment: confirm payment released (client-side pending DB in slice 3).

## Slice 3 — Backend DB increment + shelf refresh + completion toast + Reset appears
- Add `GET /api/vr/inventory/demo` and `POST /api/vr/invoice-pay/demo` to `vr_api.py` using `db.py` (mock_sap.db).
- Verify & Release Payment → server cross-check → on match UPDATE Widget-A qty += invoiced → GET new qty → shelf UI refresh → completion toast (~3s) → Reset button appears (top-right corner).
- Verify: DB row changes; shelf reflects new qty; toast shows; Reset button visible.

## Slice 4 — Reset Demo button (top-right corner)
- Restore Widget-A qty to `widgetAOriginalQty` (50) in DB; shelf back to default/EMPTY (not inbound).
- Clear `approvedPO`, lock Invoice tab (`invoiceLocked = true`), `demoComplete = false`.
- Clear voice history / transcript.
- Hide / disable Reset button after reset.
- Verify: full flow rerunnable from a single session.

## Slice 5 — Removal & rejection terminal state
- Remove Guide button (done in slice 1 nav), remove disruption panel + "check disruptions" voice command.
- PO rejection = terminal state: "PO rejected — Widget-A restock paused. Muse flagged for procurement review."; no re-run loop; Reset retries approval.
- Verify: rejection does not loop; Reset restores approval path.
