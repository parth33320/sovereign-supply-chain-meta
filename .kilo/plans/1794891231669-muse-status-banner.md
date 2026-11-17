# Muse Status Banner Plan

## Overview
Add a persistent top banner showing whether real Muse AI is active or mock mode, with a richer system prompt for the voice interpretation endpoint.

## Files to Modify
1. `backend/routers/vr.py` - Add `/vr/muse-status` endpoint + richer system prompt
2. `frontend/vr/index.html` - Banner HTML + fetch script

---

## Backend Changes (`backend/routers/vr.py`)

### 1. Add `/vr/muse-status` endpoint (after last endpoint)
```python
@router.get("/vr/muse-status")
async def muse_status():
    """Reports whether a real Muse API key is configured."""
    has_key = bool((os.environ.get("META_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip())
    demo = os.environ.get("DEMO_MODE") == "1"
    active = has_key and not demo
    return {"muse_active": active}
```

### 2. Replace system prompt in `interpret_voice` endpoint
**Find** (around line 164 in current file):
```python
    system = f"""You are SAM, a supply chain SME AI. A warehouse worker spoke a voice command.
Your job:
1. Correct speech-to-text errors (the mic may mishear supply chain terms)
2. Return the correct intent from ONLY the currently allowed actions: {allowed}
3. If the transcript doesn't match any allowed action, return intent="unknown"

Respond ONLY with JSON: {{"intent": "<intent>", "corrected": "<corrected transcript>"}}
Valid intents: restock, approve_po, reject_po, show_invoice, pay_invoice, unknown"""
```

**Replace with**:
```python
    system = f"""You are SAM (Supply chain Autonomous Manager), a supply chain AI agent running a live warehouse demo.

DEMO WORKFLOW:
- Step 1 (RESTOCK): Widget-A bin is empty. User says "restock" or "restock Widget-A" → SAM broadcasts RFQ to 3 suppliers (Apex Logistics, Global Parts Co, FastShip Inc), evaluates bids using cost/lead-time/reliability scoring, selects winner, generates draft PO for 500 units.
- Step 2 (APPROVE or REJECT PO): User reviews Purchase Order PO-2026-847 from Apex Logistics ($8.20/unit, 500 units, $4,100 total, 3-day delivery). User says "approve PO" to authorize → moves to invoice step. Or says "reject PO" / "reject" to cancel.
- Step 3 (SHOW INVOICE): After PO approved, Widget-A shows as "inbound". User says "open invoice" or "show invoice" or taps Widget-A → SAM scans invoice via Muse image recognition.
- Step 4 (PAY INVOICE): User reviews scanned invoice. Says "pay invoice" or "pay" → SAM verifies and releases payment. Demo complete: Widget-A restocked to 500 units.

REJECTION PATH: If PO rejected at Step 2, demo resets to Step 1 (restock can be triggered again).

COMMON SPEECH-TO-TEXT ERRORS TO CORRECT:
- "widget a" / "widget eight" / "widget hey" → "Widget-A"
- "approve p o" / "approve peo" / "approve" → "approve PO"
- "reject p o" / "reject peo" → "reject PO"
- "pay in voice" / "make payment" / "release payment" → "pay invoice"
- "show in voice" / "open in voice" / "check invoice" → "open invoice"
- "restock" / "re-stock" / "order more" / "replenish" → "restock"
- "apex" / "apex logistics" / "apex log" → "Apex Logistics"

YOUR TASK:
1. Correct speech-to-text errors using your knowledge of this demo's vocabulary
2. Return the correct intent from ONLY the currently allowed actions: {allowed}
3. If the transcript doesn't match any allowed action, return intent="unknown" — do NOT suggest steps the user can't take yet

Respond ONLY with JSON: {{"intent": "<intent>", "corrected": "<corrected transcript>"}}
Valid intents: restock, approve_po, reject_po, show_invoice, pay_invoice, unknown"""
```

---

## Frontend Changes (`frontend/vr/index.html`)

### 1. Add banner HTML (inside `#overlay`, before `.hud-top`)
```html
<div id="overlay">
  <div id="muse-banner" style="
    position:absolute;top:0;left:0;right:0;
    text-align:center;font-size:12px;font-weight:600;
    padding:5px 12px;z-index:20;letter-spacing:0.03em;
    background:#161b22;color:#8b949e;border-bottom:1px solid #30363d;
    pointer-events:none;
  ">⏳ Checking AI agent status…</div>
  <div class="hud-top" style="margin-top:28px;">
```

### 2. Add fetch script (before `</body>`, after existing `</script>`)
```html
<script>
(async function() {
  const banner = document.getElementById("muse-banner");
  try {
    const res = await fetch("/api/vr/muse-status");
    const data = await res.json();
    if (data.muse_active) {
      banner.style.background = "#0d1f0d";
      banner.style.color = "#3fb950";
      banner.style.borderBottom = "1px solid #238636";
      banner.textContent = "🟢 Meta Muse AI Agent active · muse-spark-1.3";
    } else {
      banner.style.background = "#1a1200";
      banner.style.color = "#d29922";
      banner.style.borderBottom = "1px solid #9e6a03";
      banner.textContent = "⚠️ Mock AI agent demo active · Set META_API_KEY env var on Render to enable Muse";
    }
  } catch {
    banner.style.color = "#f85149";
    banner.textContent = "⚠️ Mock AI agent demo active · Set META_API_KEY env var to enable Muse";
  }
})();
</script>
```

---

## Validation Checklist

- [ ] Backend `/vr/muse-status` returns `{"muse_active": true/false}`
- [ ] Banner shows "Checking AI agent status…" on load
- [ ] Real key → green banner with "🟢 Meta Muse AI Agent active · muse-spark-1.3"
- [ ] No key / DEMO_MODE → amber banner with mock warning
- [ ] Fetch error → red banner with mock warning
- [ ] `.hud-top` shifted down by 28px to avoid overlap
- [ ] System prompt in `interpret_voice` updated with full workflow description

---

## Risk Mitigation

- Banner uses inline styles to avoid CSS dependency
- Graceful fallback on fetch error
- Banner doesn't block pointer events (`pointer-events: none`)
- Existing `interpret_voice` fallback logic unchanged

---

## Files to Modify
1. `backend/routers/vr.py` — 2 changes (endpoint + system prompt)
2. `frontend/vr/index.html` — 2 changes (banner HTML + fetch script)