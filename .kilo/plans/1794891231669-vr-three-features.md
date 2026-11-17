# VR Feature Plan: A2A Log Fix, Exit AR Button, Voice Intent Backend + Tooltip

## Overview

Three independent but related features for the Supply Chain AR Walk:

1. **Feature 1**: Fix A2A log header (SAM → muse-spark-1.3) and add 3D log panel to the LEFT of PO card
2. **Feature 2**: Add "Exit AR" button to DOM overlay (visible only in AR session)
3. **Feature 3**: Backend `/api/vr/interpret-voice` endpoint with context-aware workflow state, plus frontend tooltip on Voice button

---

## Current State Analysis

### Frontend: `frontend/vr/index.html` (single `<script>` block, ~1157 lines)

- **a2aLogHTML()** at line 825-831: Header reads "A2A NEGOTIATION LOG · SAM" — needs to be "muse-spark-1.3"
- **renderPoCard()** at line 874-913: Calls `a2aLogHTML()` for DOM panel; PO spatial card rendered via `renderSpatialCard()` spec
- **spatialCardGroup** at line 381: Single `cardPlane` mesh for one card; no mechanism for secondary panels
- **DOM overlay controls** at lines 140-146: `btn-mic`, `btn-reset` in `.controls-row` — add `btn-exit-ar` here
- **startARSession()** at line 603: Success at line 628 (`xrSession` set), end handler at line 633
- **resolveIntent()** at line 1107-1117: POSTs `{transcript}` to `/api/vr/interpret-voice` — needs `workflow_state`
- **Voice recognition** at lines 1132-1144: `recognition.onresult` calls `handleIntent()` — add HUD tooltip update

### Backend: `backend/routers/vr.py` (168 lines)

- Existing endpoints: `/vr/negotiate`, `/vr/invoice-scan`, `/vr/invoice-pay`, `/vr/reset-demo`
- Uses `get_llm()` from `llm_client` for Muse calls
- `SAM_SYSTEM_PROMPT` for negotiation — need new prompt for voice intent interpretation
- No `InterpretVoiceRequest` model or `/vr/interpret-voice` endpoint yet

---

## Feature 1: A2A Log Header + 3D Log Panel

### Changes to `frontend/vr/index.html`

#### 1a. Fix a2aLogHTML() header (line 827)
```javascript
// FIND:
<div style="font-size:11px;font-weight:700;color:var(--accent);letter-spacing:.05em;margin-bottom:6px;">A2A NEGOTIATION LOG · SAM</div>
// REPLACE:
<div style="font-size:11px;font-weight:700;color:var(--accent);letter-spacing:.05em;margin-bottom:6px;">A2A NEGOTIATION LOG · muse-spark-1.3</div>
```

#### 1b. Extend spatialCardGroup to support secondary "log panel" mesh
Currently `spatialCardGroup` has one `cardPlane` (created at line 403-407). We need:
- Keep existing `cardPlane` for main PO card
- Add a new named mesh `a2aLogMesh` for the log panel, positioned to the LEFT

**Implementation approach**: In `renderPoCard()`, after calling `renderSpatialCard()` for the PO card, create and add a separate canvas-texture plane to `spatialCardGroup`.

```javascript
// In renderPoCard(), AFTER the openPanel() + renderSpatialCard() call (around line 910):

// Remove old a2aLog mesh if exists
const oldLog = spatialCardGroup.getObjectByName("a2aLogMesh");
if (oldLog) {
  if (oldLog.material.map) oldLog.material.map.dispose();
  oldLog.material.dispose();
  spatialCardGroup.remove(oldLog);
}

// Create a2a log panel to the LEFT of PO card
const logCanvas = document.createElement("canvas");
logCanvas.width = 512; logCanvas.height = 320;
const logCtx = logCanvas.getContext("2d");
// Draw dark background with rounded corners
logCtx.fillStyle = "#0d1117";
logCtx.beginPath();
logCtx.roundRect(0, 0, 512, 320, 16);
logCtx.fill();
// Draw header
logCtx.fillStyle = "#58a6ff";
logCtx.font = "bold 20px monospace";
logCtx.textAlign = "left";
logCtx.fillText("A2A NEGOTIATION LOG · muse-spark-1.3", 16, 36);
// Draw log entries
logCtx.font = "16px monospace";
logCtx.fillStyle = "#c9d1d9";
a2aLog.forEach((l, i) => {
  logCtx.fillText(l.icon + " " + l.text.replace(/<[^>]+>/g, ""), 16, 70 + i * 36);
});
const logTex = new THREE.CanvasTexture(logCanvas);
const logMat = new THREE.MeshBasicMaterial({ map: logTex, transparent: true, side: THREE.DoubleSide });
const logMesh = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.32), logMat);
logMesh.name = "a2aLogMesh";
logMesh.position.set(-0.55, 0, 0.01);  // left of PO card, slight z-offset to avoid z-fighting
spatialCardGroup.add(logMesh);
```

**Note**: The PO card is positioned at `spatialCardGroup.position.set(-0.39, 1.50, 0.06)` (line 479). The `logMesh` at local `(-0.55, 0, 0.01)` puts it 0.55m to the left of the PO card center with a 0.01m z-offset to avoid z-fighting with the main cardPlane.

---

## Feature 2: Exit AR Button

### Changes to `frontend/vr/index.html`

#### 2a. Add button HTML in DOM overlay (after line 143)
```html
<!-- FIND: -->
<button class="btn btn-ghost interactive" id="btn-reset">🔄 Reset Demo</button>
<!-- ADD AFTER: -->
<button class="btn btn-ghost interactive" id="btn-exit-ar" style="display:none;">🚪 Exit AR</button>
```

#### 2b. Show button on AR session start (in startARSession, after line 643)
```javascript
document.body.classList.add("xr-active");
document.getElementById("btn-exit-ar").style.display = "";  // ADD
setStatus("🥽 Starting AR…", true);
```

#### 2c. Hide button on AR session end (in session end handler, after line 640)
```javascript
document.body.classList.remove("xr-active");
document.getElementById("btn-exit-ar").style.display = "none";  // ADD
setStatus("Supply Chain AR · Ready");
```

#### 2d. Add click handler (after line 1151, near other button listeners)
```javascript
document.getElementById("btn-exit-ar").addEventListener("click", async () => {
  if (xrSession) { try { await xrSession.end(); } catch(e) {} }
});
```

---

## Feature 3: Backend Voice Intent + Context-Aware Tooltip

### 3A: Backend — `backend/routers/vr.py`

#### 3A-1: Add Pydantic model (after line 89, before `/vr/negotiate`)
```python
class InterpretVoiceRequest(BaseModel):
    transcript: str
    workflow_state: dict = {}  # {pending_po, approved_po, active_invoice, bin_status}
```

#### 3A-2: Add endpoint (after `/vr/reset-demo`, before EOF)
```python
@router.post("/vr/interpret-voice")
async def interpret_voice(req: InterpretVoiceRequest):
    """muse-spark-1.3 supply chain SME: corrects transcript + returns valid intent given workflow state."""
    state = req.workflow_state
    # Build allowed intents based on workflow state
    allowed = []
    if not state.get("pending_po"):
        allowed.append("restock")
    if state.get("pending_po") and not state.get("approved_po"):
        allowed += ["approve_po", "reject_po"]
    if state.get("approved_po") and not state.get("active_invoice"):
        allowed.append("show_invoice")
    if state.get("active_invoice"):
        allowed.append("pay_invoice")

    system = f"""You are SAM, a supply chain SME AI. A warehouse worker spoke a voice command.
Your job:
1. Correct speech-to-text errors (the mic may mishear supply chain terms)
2. Return the correct intent from ONLY the currently allowed actions: {allowed}
3. If the transcript doesn't match any allowed action, return intent="unknown"

Respond ONLY with JSON: {{"intent": "<intent>", "corrected": "<corrected transcript>"}}
Valid intents: restock, approve_po, reject_po, show_invoice, pay_invoice, unknown"""

    try:
        from llm_client import get_llm
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=f"Transcript: {req.transcript}"),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        result = json.loads(raw.strip())
        return {"intent": result.get("intent", "unknown"), "corrected": result.get("corrected", req.transcript)}
    except Exception as e:
        # Fallback: keyword match
        t = req.transcript.lower()
        if "restock" in t or "widget" in t or "order" in t: intent = "restock"
        elif "approve" in t or "accept" in t: intent = "approve_po"
        elif "reject" in t or "cancel" in t: intent = "reject_po"
        elif "invoice" in t or "bill" in t: intent = "show_invoice"
        elif "pay" in t or "settle" in t: intent = "pay_invoice"
        else: intent = "unknown"
        # Only return if allowed
        if intent not in allowed: intent = "unknown"
        return {"intent": intent, "corrected": req.transcript}
```

**Note**: Uses `llm.ainvoke()` with `SystemMessage`/`HumanMessage` matching existing `/vr/negotiate` pattern. `json` is already imported at the top of `vr.py`.

---

### 3B: Frontend — Pass workflow state in `resolveIntent()` (line 1109-1111)

```javascript
// FIND:
body:JSON.stringify({transcript})
// REPLACE:
body:JSON.stringify({
  transcript,
  workflow_state: {
    pending_po: !!pendingPO,
    approved_po: !!approvedPO,
    active_invoice: !!activeInvoice,
    bin_status: bins[0]?.status
  }
})
```

---

### 3C: Frontend — Context-Aware Tooltip on Voice Button

#### 3C-1: Add helper function (before button event listeners, around line 1145)
```javascript
function getVoiceTooltip() {
  if (!pendingPO && (!bins[0] || bins[0].status === "empty"))
    return 'Say: "restock Widget-A" to trigger A2A procurement';
  if (pendingPO && !approvedPO)
    return 'Say: "approve PO" or "reject PO"';
  if (approvedPO && !activeInvoice)
    return 'Say: "open invoice" to validate delivery';
  if (activeInvoice)
    return 'Say: "pay invoice" to complete payment';
  return 'Say: "restock Widget-A" to restart demo';
}
```

#### 3C-2: Add mouseenter/mouseleave tooltip on DOM Voice button (before line 1146)
```javascript
let tooltipEl = null;
btnMic.addEventListener("mouseenter", () => {
  tooltipEl = document.createElement("div");
  tooltipEl.style.cssText = "position:absolute;bottom:60px;left:50%;transform:translateX(-50%);background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:8px;padding:8px 12px;font-size:12px;white-space:nowrap;z-index:999;pointer-events:none;";
  tooltipEl.textContent = getVoiceTooltip();
  btnMic.style.position = "relative";
  btnMic.parentElement.style.position = "relative";
  btnMic.parentElement.appendChild(tooltipEl);
});
btnMic.addEventListener("mouseleave", () => {
  if (tooltipEl) { tooltipEl.remove(); tooltipEl = null; }
});
```

#### 3C-3: Update 3D HUD status after voice command resolves (in `recognition.onresult`, after line 1140)
```javascript
recognition.onresult = async e => {
  const transcript = e.results[e.results.length-1][0].transcript;
  const intent = await resolveIntent(transcript);
  showVoiceFeedback(transcript, intent, INTENT_LABELS[intent]||intent);
  handleIntent(intent);
  // Update HUD with next-step hint
  setTimeout(() => update3DHudStatus(getVoiceTooltip()), 1500);
};
```

#### 3C-4: (Optional) Update 3D Voice button label when state changes
The `set3DMicListening()` function updates the 3D mic button texture. We could also update it to show the current tooltip when not listening, but that's more complex. The HUD status update above is sufficient for MVP.

---

## Implementation Order & Dependencies

| Order | Task | Depends On |
|-------|------|------------|
| 1 | Feature 1a: Fix a2aLogHTML header | None |
| 2 | Feature 1b: Add a2aLogMesh in renderPoCard | Feature 1a |
| 3 | Feature 2a: Exit AR button HTML | None |
| 4 | Feature 2b/2c: Show/hide in startARSession/end | Feature 2a |
| 5 | Feature 2d: Exit AR click handler | Feature 2a |
| 6 | Feature 3A: Backend endpoint | None (independent file) |
| 7 | Feature 3B: Frontend workflow_state in resolveIntent | Feature 3A (endpoint must exist) |
| 8 | Feature 3C: Tooltip + HUD update | Feature 3B |

---

## Validation Checklist

### Feature 1
- [ ] a2aLogHTML() header shows "muse-spark-1.3" in DOM panel
- [ ] 3D log panel appears to the LEFT of PO card in AR
- [ ] Log panel updates when new negotiation occurs
- [ ] Old log panel removed on subsequent negotiations

### Feature 2
- [ ] "Exit AR" button hidden in 2D mode
- [ ] "Exit AR" button visible in AR session
- [ ] Clicking exits AR session cleanly
- [ ] Button hides again after exit

### Feature 3
- [ ] Backend `/api/vr/interpret-voice` returns `{intent, corrected}` JSON
- [ ] Intent respects workflow state (e.g., "approve_po" not allowed before pending_po)
- [ ] Fallback works when Muse unavailable
- [ ] Frontend sends workflow_state in request
- [ ] DOM Voice button shows tooltip on hover
- [ ] 3D HUD status updates with next-step hint after voice command

---

## Risk Mitigation

- **spatialCardGroup z-fighting**: Log panel at same z as PO card — use slight z-offset (0.01) or ensure rendering order
- **Canvas texture memory**: Dispose old `logTex` when replacing log panel
- **Backend LLM availability**: Graceful fallback to keyword matching (already in plan)
- **Tooltip positioning**: Use `btnMic.parentElement` (`.controls-row`) as anchor — verify it has `position: relative`
- **AR session end race**: `xrSession.end()` is async; button click handler awaits it

---

## Files to Modify

1. `frontend/vr/index.html` — 7 edits across the script block
2. `backend/routers/vr.py` — 2 additions (model + endpoint)

---

## Out of Scope

- 3D Voice button label update (complex canvas redraw)
- Persistent tooltip on 3D mic button (requires raycast hover detection)
- Multi-language support for tooltips
- Voice command history panel