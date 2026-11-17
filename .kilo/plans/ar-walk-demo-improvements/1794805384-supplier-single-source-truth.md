# Plan: Supplier Single Source of Truth + agent_status DB-backed + Discrepancy Simplification

## Context
Three places hardcode supplier names/prices that disagree:
- `frontend/vr/index.html:1074-1079` — A2A steps use `MegaSupply Co: $8.95/5d` and `FastParts Inc: $9.10/2d` (names don't match elsewhere)
- `frontend/src/components/HITLCard.jsx:7,17-19` — default supplier `FastShip Supply`, quotes order implies FastShip ($8.10/3d) wins
- `graph.py:253-263` (DEMO_MODE) — quotes Apex $8.50/4d, Global Parts $8.75/6d, FastShip $8.10/3d → FastShip wins, contradicting desired single source where Apex wins

Also:
- `vr_api.py:39-65` — `agent_status()` returns hardcoded strings, never reads DB, no thread_id persistence
- `frontend/vr/index.html:1040-1064` — `flagDiscrepancy()` has too much text; simplify to alert triangle + "Pending Supplier Response for Discrepancy" title only
- Frontend does NOT currently poll `/api/vr/agent-status/{thread_id}` or generate a thread_id

## Single source of truth (all three must match)
| Supplier | Price/unit | Lead time | Role |
|---|---|---|---|
| Apex Logistics | $8.20 | 3 days | Winner / recommended |
| Global Parts Co | $8.75 | 6 days | |
| FastShip Supply | $9.10 | 2 days | |

## Ordered tasks

### 1. Fix supplier data in `frontend/vr/index.html` (lines 1074-1079)
- `"💬 MegaSupply Co: $8.95/unit · 5 days"` → `"💬 Global Parts Co: $8.75/unit · 6 days"`
- `"💬 FastParts Inc: $9.10/unit · 2 days"` → `"💬 FastShip Supply: $9.10/unit · 2 days"`
- Best deal line already says Apex Logistics $8.20 · 3 days — keep as-is

### 2. Fix supplier data in `frontend/src/components/HITLCard.jsx`
- Line 7: default `supplier` → `"Apex Logistics"`
- Lines 17-19: quotes array → Apex Logistics $8.20/3d (winner), Global Parts Co $8.75/6d, FastShip Supply $9.10/2d
- Lines 21-24 `rec` default reasoning → reference Apex Logistics at $8.20/3 days

### 3. Fix supplier data in `graph.py` DEMO_MODE block (lines 253-263)
- quotes → Apex Logistics $8.20/3d, Global Parts Co $8.75/6d, FastShip Supply $9.10/2d
- recommendation → `selected_supplier: "Apex Logistics"`, reasoning referencing $8.20/3d
- SUPPLIER_PERSONAS (line 229) already correct — no change

### 4. Create `agent_threads` table in `init_db.py`
- Add to both `init_sqlite()` and `init_postgres()`:
  ```sql
  CREATE TABLE IF NOT EXISTS agent_threads (
    thread_id TEXT PRIMARY KEY,
    transcript TEXT,
    draft_po TEXT,
    status TEXT DEFAULT 'running',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )
  ```

### 5. Persist transcript + draft_po from `graph.py` (real-graph path)
- In `a2a_negotiate_sync()` after building `a2a_transcript`, and/or in `draft_po()` after building `pending_po`:
  ```python
  thread_id = state.get("thread_id") or state.get("request_id") or "req-default"
  execute_mutation(
    "INSERT OR REPLACE INTO agent_threads (thread_id, transcript, draft_po, status) VALUES (?,?,?,?)",
    (thread_id, json.dumps(a2a_transcript), json.dumps(pending_po), "done")
  )
  ```
- thread_id source = `state.get("thread_id")` fallback `state.get("request_id")`.
- Note: for the VR demo path (no real graph wired), step 7 below simulates this write instead.

### 6. Rework `agent_status()` in `vr_api.py`
- Accept `thread_id` as real identifier
- Query `agent_threads WHERE thread_id = ?`
- If row found with status `done`: convert `a2a_transcript` entries to display `lines`, return `done: true` + `draft_po` from DB
- If row found with status `running`: return `{"lines": ["⏳ Negotiating..."], "done": false}`
- If no row and `DEMO_MODE=1`: fall back to current hardcoded strings (done: true)
- If no row and not DEMO_MODE: return `{"lines": ["⏳ Negotiating..."], "done": false}`

### 7. Frontend polls `agent-status` and displays A2A feed (simulate storage)
- Decision (resolved): simulate storage — **no new graph-trigger endpoint**. On restock trigger, frontend generates `thread_id = "vr-${Date.now()}"` and seeds `agent_threads` with demo transcript + draft_po via a lightweight backend write on the restock trigger path (avoids a dedicated endpoint; keeps demo-day simple).
- In `triggerAgentRestock()`: generate `thread_id`, seed `agent_threads` (demo transcript = the existing `steps` array; draft_po = Apex Logistics PO at $8.20/3d, qty 500, total $4,100), then start polling.
- Add polling: `setInterval`/recursive fetch of `/api/vr/agent-status/{thread_id}` until `done === true`; render each `line` into `#agent-lines` as the AR negotiation feed.
- When `done`, use `draft_po` from response to populate the PO card (supplier, sku, qty, unit_price, total, lead_time) and render approve/reject buttons.
- Keep the existing local `steps` array as the demo transcript source for seeding.

### 8. Simplify `flagDiscrepancy()` container (lines 1040-1064)
- Keep: ⚠️ alert triangle (48px), title → "Pending Supplier Response for Discrepancy"
- Delete: "Amounts do not match the approved PO." line, `dispute-card` block, `pending-response` div, production credit-memo line, "Re-open Invoice" button

## Open decisions
- None resolved as open. thread_id sourcing = `vr-${Date.now()}` generated in `triggerAgentRestock()`; simulate-storage chosen over new endpoint (user decision 2026-11-15).

## Validation criteria
- All three files show identical supplier names/prices: Apex $8.20/3d (winner), Global Parts $8.75/6d, FastShip $9.10/2d
- `agent_status({thread_id})` returns DB-backed transcript + draft_po, falling back to hardcoded only in DEMO_MODE with no row
- `flagDiscrepancy()` shows only ⚠️ + "Pending Supplier Response for Discrepancy", no extra text/buttons
- Frontend polls agent-status until done and renders A2A lines + PO card from `draft_po`
