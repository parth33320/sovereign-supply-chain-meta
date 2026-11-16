# Architecture: S26 — VR Voice Intent + Demo Polish

## Fit
- `vr_api.py` — FastAPI bridge that serves `frontend/vr/index.html` and the demo endpoints. Gains one intent-classification endpoint.
- `frontend/vr/index.html` — single-file WebXR/DOM-overlay client. Loses the nav bar; gains contextual invoice routing and a voice-intent dispatch layer.
- `mock_sap.db` — unchanged schema; `agent_threads` and `inventory` are touched only through existing endpoints.

## Endpoints
- `POST /api/vr/interpret-voice` — classify a transcript into `restock | approve_po | reject_po | pay_invoice | show_invoice | unknown`, returning `{intent, item}`.
- Existing: `POST /api/vr/shelf-scan/demo`, `POST /api/vr/invoice-scan/demo`, `POST /api/vr/agent-threads/{id}`, `GET /api/vr/agent-status/{id}`, `POST /api/vr/invoice-pay/demo`, `POST /api/vr/reset-demo`.

## Data
- No schema changes. `agent_threads` rows are seeded per A2A run and polled once.

## Flow
1. Pinch right on shelf → `onShelfPinch` → `shelf-scan/demo` → `renderShelfResult` → floating card.
2. Restock → `triggerAgentRestock` → seed thread → poll `agent-status` → `renderPoCard`.
3. Approve (pinch or voice) → `approveAgentPO` → `invoiceLocked = false` → shelf bin A becomes inbound.
4. Pinch Widget-A again → `onShelfPinch` sees `invoiceLocked === false` → `showScene("invoice")`.
5. Pinch invoice → `onInvoicePinch` → `invoice-scan/demo` → `renderInvoiceResult` → pay → `invoice-pay/demo` → stock update.

## External
- `muse-spark-1.3` via the OpenAI-compatible Meta endpoint. Key resolution: `MUSE_API_KEY` → `META_API_KEY`; base URL `MUSE_BASE_URL` → `META_API_BASE_URL` → `https://api.meta.ai/v1`.

## Call stack — voice command

```text
└── [Project] Quest DOM overlay (frontend/vr/index.html)
    ├── [Folder] Browser (Web Speech API)
    │   └── [File] frontend/vr/index.html
    │       └── [Class] SpeechRecognition instance (recognition)
    │           └── [Method] onresult(event)
    │               ├── [Variable State Shift] transcript = "approve the po" (raw → lowercase)
    │               ├── [Method] resolveIntent(transcript)
    │               │   └── [Project] HTTP POST /api/vr/interpret-voice
    │               │       └── [Folder] vr_api.py
    │               │           └── [Method] interpret_voice(payload)
    │               │               ├── [Variable State Shift] api_key = env MUSE_API_KEY | META_API_KEY | None
    │               │               ├── [Variable State Shift] content = LLM JSON string | None
    │               │               └── [Method] _parse_intent_json(content)
    │               │                   └── [Variable State Shift] {"intent": "approve_po", "item": null}
    │               ├── [Method] showVoiceFeedback(transcript, intent, label)
    │               │   └── [Variable State Shift] #voice-feedback.innerHTML = heard + intent + hint
    │               └── [Method] handleIntent(intent, transcript)
    │                   └── [Variable State Shift] approve_po → approveAgentPO()
    └── [Method] approveAgentPO()
        ├── [Variable State Shift] pendingPO = null; approvedPO = draft PO
        ├── [Method] openPanel(stateHtml, "ok")
        │   └── [Variable State Shift] body.classList = panel-open (scenes dim)
        ├── [Method] updateShelfToInbound()
        │   └── [Variable State Shift] fill.className = bin-bar-fill inbound
        └── [Variable State Shift] invoiceLocked = false
```

## Call stack — pinch

```text
└── [Project] WebXR session (navigator.xr)
    ├── [Folder] XRFrame loop
    │   └── [File] frontend/vr/index.html
    │       └── [Method] onXRFrame(time, frame)
    │           ├── [Method] detectPinch(frame, handRight)
    │           │   └── [Variable State Shift] thumb↔index distance 0.031 → 0.018 (< 0.025)
    │           ├── [Method] pulseHaptic(handRight)
    │           │   └── [Project] XR gamepad haptic actuator (70ms, 0.6)
    │           ├── [Method] setPinchVisual("right", true)
    │           │   └── [Variable State Shift] .pinch-indicator--right += pinch-active
    │           └── [Method] onShelfPinch()
    │               ├── [Variable State Shift] invoiceLocked false → showScene("invoice")
    │               └── [Method] onShelfPinch (locked) → shelf-scan/demo → renderShelfResult
    └── [Method] onShelfPinch()
        └── [Variable State Shift] invoiceLocked false → showScene("invoice")`