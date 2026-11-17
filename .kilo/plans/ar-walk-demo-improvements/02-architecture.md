# Architecture: AR Walk — Demo Improvements

## Boundaries
- Project: same-origin browser tab serving `frontend/vr/index.html`, backed by `vr_api.py` (uvicorn FastAPI, port 8502).
- Data store: SQLite `mock_sap.db` via `db.py` (Tenant_A, Widget-A seeds at 50 units).
- No new frontend build step — `index.html` is a single static HTML/JS file.

## Modules & Seams
- `frontend/vr/index.html` — single-page AR Walk UI; global JS demo state drives Shelf/Invoice scenes, nav, mic button, tooltips, toasts, and AR panel.
- `backend/vr_api.py` — existing FastAPI app; add two demo endpoints that read/write `mock_sap.db` through `db.py`.
- `backend/db.py` — existing unified DB access layer (SELECT + mutation helpers); reused unchanged.

## Data Flow (verbatim Mermaid)
```mermaid
flowchart LR
    J[(Judge)] -->|pinch / voice| UI[frontend/vr/index.html]
    UI -->|approve PO| S[Shelf scene: Widget-A inbound]
    S -->|unlock| INV[Invoice tab unlocked]
    INV -->|pinch / "check invoice"| SCAN[/api/vr/invoice-scan/demo]
    SCAN -->|extraction| CC{cross-check vs approved PO}
    CC -->|match| PAY[Verify & Release Payment]
    CC -->|delta| DISC[Flag Discrepancy → dispute card]
    PAY -->|POST /api/vr/invoice-pay/demo| DB[(mock_sap.db: Widget-A qty += invoiced)]
    DB -->|new qty| UI[Shelf UI refresh]
    UI -->|completion toast| RT[Reset Demo button, top-right corner]
    RT -->|POST reset| DB2[(mock_sap.db: Widget-A qty = 50)]
    DB2 -->|default state| UI
```

## Types & Signatures
Frontend (`index.html` implicit state):
- `state = { invoiceLocked: boolean, approvedPO: PO|null, micActive: boolean, widgetAOriginalQty: number, demoComplete: boolean, resetBtnVisible: boolean, disputeDraft: string|null }`
- `unlockInvoiceTab(): void`
- `crossCheckAgainstPO(inv, po): {match: boolean, confidence: number, delta: number|null}`
- `onVerifyPayment(): Promise<void>`
- `onFlagDiscrepancy(): void`
- `onResetDemo(): Promise<void>`
- `showCompletionToast(qty: number): void`
- `startVoiceListening(): void` — sets `micActive=true` only while recording

Backend (`vr_api.py`):
- `GET /api/vr/inventory/demo -> {items: [{sku, qty, tenant_id}]}`
- `POST /api/vr/invoice-pay/demo(body:{po, invoice}) -> {status, match, confidence, delta, disputeDraft, newQty}` — server cross-check; on match `UPDATE inventory SET quantity = quantity + invoice.qty WHERE tenant_id='Tenant_A' AND item_name='Widget-A'`

## Decision Record
- Invoice cross-check is client-side in demo mode (no API key) with authoritative server validation in `invoice-pay`; fallback message "✅ All fields match PO #2026-847".
- PO rejection is a terminal state (no re-run loop) per product decision; Reset is the escape hatch.
- Disruption panel, "check disruptions" command, and Guide button are removed.
