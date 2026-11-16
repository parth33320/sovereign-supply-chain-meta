# Slices: S26 — VR Voice Intent + Demo Polish

1. **Tracer bullet** — `POST /api/vr/interpret-voice` returns `{intent, item}`; frontend calls it and falls back to keyword matching. Verified by unit tests + a manual curl.
2. **Real path** — intent dispatch: `restock / approve_po / reject_po / pay_invoice / show_invoice`, with `show_voice_feedback` rendered before any action fires.
3. **Contextual invoice** — delete `#nav-bar`, `#btn-invoice`, `#invoice-tooltip` and their CSS/JS; `onShelfPinch` branches on `invoiceLocked`; left-pinch and voice obey the same gate.
4. **Visual polish** — Inter + antialiasing; one card system (`card`, `card__*`) replaces every inline style; A2A panel becomes a 420px floating card with scene dimming and an entrance animation; pinch feedback is edge-triggered with haptics and eased transitions.
5. **Regression** — repair the fatal `approveAgentPO` syntax error, orphaned CSS declarations, malformed Verify button, undefined `approvePo/rejectPo/payInvoice`, dead `handleVoiceCommand`/`simulateVoice`, incomplete `resetDemo`, and the voice-feedback clearing race.

## Verification
- `pytest tests/test_vr_voice_intent.py -q`
- `pytest tests/test_s23_inventory.py tests/test_voice_handler.py -q` (no regressions)
- HTML script extracted and parsed with `node --check`
- Manual: `uvicorn vr_api:app --port 8502` + Playwright walkthrough of shelf → A2A → approve → invoice → pay