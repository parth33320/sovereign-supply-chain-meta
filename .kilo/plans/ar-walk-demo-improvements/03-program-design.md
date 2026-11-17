# Program Design: AR Walk — Demo Improvements

## Call Stack Trace

Execution Call Stack Trace:
└── [Project] Supply Chain AR Walk Demo (browser tab, same-origin vr_api:8502)
    ├── [Configuration/Env] META_API_KEY optional, DEMO_MODE=1, mock_sap.db (SQLite)
    └── [Folder] frontend/vr
        └── [File] index.html
            └── [Class] DemoApp (implicit global JS state)
                ├── [Variable State Shift] invoiceLocked = true (Invoice tab greyed/locked on load)
                ├── [Variable State Shift] approvedPO = null
                ├── [Variable State Shift] micActive = false
                ├── [Variable State Shift] widgetAOriginalQty = 50 (from GET /api/vr/inventory/demo)
                └── [Method] onShelfPinch() / voice "restock Widget-A"
                    ├── [Method] triggerAgentRestock()
                    │   └── [Project] Remote Boundary (hardcoded A2A negotiation simulation)
                    │   └── [Variable State Shift] restockTriggered = true
                    ├── [Method] approveAgentPO()
                    │   ├── [Variable State Shift] approvedPO = {Apex Logistics, Widget-A, 500, $8.20, $4100, PO#2026-847}
                    │   ├── [Variable State Shift] shelf Widget-A → "inbound" state (fill purple, qty "⏳ inbound")
                    │   ├── [Method] unlockInvoiceTab()
                    │   │   └── [Variable State Shift] invoiceLocked = false (Invoice tab enabled)
                    │   └── [Variable State Shift] setStatus("✅ PO approved · Widget-A restocking")
                └── [Method] onInvoicePinch() / voice "check invoice" (blocked while invoiceLocked)
                    ├── [Method] fetch /api/vr/invoice-scan/demo
                    │   └── [File] vr_api.py
                    │       └── [Method] invoice_scan_demo() -> {supplier, sku, qty, unit_price, total}
                    ├── [Variable State Shift] invoiceExtraction = {...}
                    ├── [Method] crossCheckAgainstPO(extraction, approvedPO)
                    │   ├── [Variable State Shift] matchConfidence = 1.0 (no API key fallback: "✅ All fields match PO #2026-847")
                    │   └── [Variable State Shift] delta = null (or unit-price diff)
                    ├── [Branch] match ? "Verify & Release Payment" : "Flag Discrepancy"
                    │   ├── [Method] onVerifyPayment()
                    │   │   ├── [Method] POST /api/vr/invoice-pay/demo {po, invoice}
                    │   │   │   └── [File] vr_api.py
                    │   │   │       └── [Method] invoice_pay_demo()
                    │   │   │           ├── [Variable State Shift] match validated server-side
                    │   │   │           ├── [Method] UPDATE inventory SET quantity = quantity + 500 WHERE tenant_id='Tenant_A' AND item_name='Widget-A'
                    │   │   │           │   └── [File] db.py → mock_sap.db
                    │   │   │           └── [Variable State Shift] Widget-A qty 50 → 550
                    │   │   ├── [Method] GET /api/vr/inventory/demo -> newQty
                    │   │   ├── [Variable State Shift] shelf Widget-A → newQty, status ok (not inbound)
                    │   │   └── [Method] showCompletionToast(newQty)
                    │   │       └── [Variable State Shift] demoComplete = true, resetBtnVisible = true
                    │   └── [Branch] mismatch → onFlagDiscrepancy()
                    │       ├── [Method] buildDisputeDraft() -> "Invoice shows $8.50/unit; PO locked $8.20/unit — requesting credit memo for $150 difference"
                    │       ├── [Variable State Shift] disputeDraftVisible = true (dismissible card)
                    │       └── [Variable State Shift] invoiceState = "Pending supplier response"
                └── [Method] onResetDemo() (top-right corner button)
                    ├── [Method] reset Widget-A qty in mock_sap.db (UPDATE ... quantity = 50)
                    │   └── [File] db.py → mock_sap.db
                    ├── [Variable State Shift] Widget-A qty → 50, shelf → default/EMPTY (not inbound)
                    ├── [Variable State Shift] approvedPO = null, invoiceLocked = true, demoComplete = false
                    ├── [Variable State Shift] voice history / transcript cleared
                    └── [Variable State Shift] resetBtnVisible = false

## Files
- `frontend/vr/index.html`: nav lock + Invoice tooltip, mic hover tooltip + mic-active Listening gate, invoice scene reframe, Verify/Flag handlers, completion toast, Reset button, remove Guide/disruption.
- `backend/vr_api.py`: add `GET /api/vr/inventory/demo` and `POST /api/vr/invoice-pay/demo`.
- `backend/db.py`: reused unchanged (existing SELECT + mutation helpers).

## Types & Signatures
```python
# vr_api.py additions
GET /api/vr/inventory/demo -> {"items": [{"sku": str, "qty": int, "tenant_id": str}]}
POST /api/vr/invoice-pay/demo
  body: {"po": {"supplier","sku","qty","unit_price","total","po_id"}, "invoice": {"supplier","sku","qty","unit_price","total"}}
  -> {"status":"paid"|"discrepancy","match":bool,"confidence":float,"delta":float|null,"disputeDraft":str|null,"newQty":int}
```

## Test Plan
- Invoice tab greyed/locked on load; hover/focus shows tooltip "Complete voice or pinch restock to generate a supplier invoice"; unlocks after PO approval + shelf shows Widget-A inbound.
- "Listening..." renders only while `micActive` (recording), never on initial load or after session ends.
- Mic hover/focus tooltip lists: restock Widget-A · approve · reject · check invoice · show shelf; dismisses on mouse-out / tap-away.
- Verify & Release Payment increments Widget-A qty in `mock_sap.db` (Tenant_A), refreshes shelf UI, shows completion toast ~3s, then Reset button visible.
- Flag Discrepancy shows dismissible dispute draft + "Pending supplier response" state; note "In production, Muse would monitor for the supplier's credit memo."; demo does not lock up.
- Reset Demo restores Widget-A qty to 50 in DB, shelf to default (not inbound), locks Invoice tab, clears approved PO/invoice state and voice history/transcript.
- PO rejection = terminal state "PO rejected — Widget-A restock paused. Muse flagged for procurement review."; no re-run loop; Reset retries approval.
- Guide button, disruption panel, and "check disruptions" voice command removed.
- Backend: invoice-pay on match → DB increment + newQty; on delta → discrepancy, no DB change, disputeDraft returned.

## Validation Commands
- Frontend: open `frontend/vr/index.html` in a browser against a running `uvicorn vr_api:app --port 8502`; no build step (no `npm run` needed for the HTML demo). Lint the React dashboard separately: `cd frontend && npm run lint` (oxlint) — out of scope for this change.
- Backend: `pytest tests/` (existing suite) to ensure no regressions; optionally add a test for the new `invoice-pay`/`inventory` demo endpoints.
