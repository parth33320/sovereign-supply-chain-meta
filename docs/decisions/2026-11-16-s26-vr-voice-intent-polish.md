# Decision Log: 2026-11-16 — S26 VR Voice Intent + Demo Polish

## Context

The AR walk had an abandoned, uncommitted attempt at voice intent + visual polish. Before changing anything, the rubric violations in that attempt were recorded here (rubric §1.4: log violations before fixing):

1. **Fatal syntax error** — `approveAgentPO()` contained an orphaned object-literal fragment (`supplier: "Apex Logistics", …`) at top level, so the entire `<script>` block failed to parse and nothing on the page worked (violates §4: unhandled breakage; §2: no dead code).
2. **Malformed markup** — the "Verify & Release Payment" button closed its `style` attribute early, rendering raw CSS text as the button label.
3. **Orphaned CSS** — stray declarations (`margin-top: 2px; …`) sat outside any rule after `.pinch-hint`, which swallowed the `#invoice-scene` rule.
4. **Undefined handlers** — the voice handler called `approvePo()`, `rejectPo()`, `payInvoice()`, none of which exist.
5. **Dead code** — `handleVoiceCommand()`, `simulateVoice()`, `dispute-card`, `pending-response`, `dismissible`, `nav-btn` and `#invoice-tooltip` were unreachable.
6. **No error handling / hardcoded values** — the new endpoint had no try/except, imported `httpx` and `os` inline, used a non-existent `MUSE_API_KEY` with no fallback, and could return a raw LLM string (violates §2: try/except + env defaults; §6: portability).
7. **Voice feedback race** — `#voice-feedback` lived inside `#ar-panel`, whose `innerHTML` is replaced on every render and which starts `display:none`, so feedback was destroyed or invisible; `onend` cleared it immediately after every command.

## Decision

- Keep the demo's data contract intact: Widget-A stays seeded at 50 in `mock_sap.db` because `tests/test_s23_inventory.py` asserts it; the shelf overlay starts at 0 as the stockout narrative.
- Add exactly one intent vocabulary shared by both sides: `restock | approve_po | reject_po | pay_invoice | show_invoice | unknown`. The LLM prompt and the frontend `INTENT_LABELS` map are the single source of truth for labels.
- The endpoint never raises: missing key, upstream failure, malformed JSON, and out-of-vocabulary intents all degrade to `{"intent": "unknown", "item": null}` so the client always has a valid action.
- Voice feedback is a top-level fixed element under the status pill, not a child of `#ar-panel`, because the panel is re-rendered wholesale and starts hidden. It is cleared when a new listening session starts, when the mic is explicitly toggled off, and on reset — never on the automatic `onend` that follows a successful command.
- The nav bar is removed entirely. The invoice is reached contextually: right-pinch on Widget-A while `invoiceLocked` runs the restock flow; after PO approval the same pinch opens the invoice. Left-pinch and voice obey the same gate.
- The A2A/result panel stays a floating 420px centered card, but scenes dim to 14% and stop receiving pointer events while it is open, so the card reads as a modal layer instead of a sheet covering content.
- Pinch feedback is edge-triggered (down → glow + haptic, up → clear) rather than a 300ms global timer, and the class is removed per-hand on release.

## Verification

- `pytest tests/test_vr_voice_intent.py -q` — 16 passed (happy path, fenced/prose JSON, unknown intent, no key, upstream error, empty/missing transcript, parser matrix).
- `node --check` on the extracted `<script>` — syntax OK; zero inline `style=` attributes remain in generated markup.
- HTML parser validation — balanced tags, balanced CSS braces, no duplicate IDs.
- Regression: `tests/test_s23_inventory.py`, `tests/test_voice_handler.py` pass.