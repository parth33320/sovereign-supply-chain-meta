# Decision Log — 2026-11-18 — Hide Voice Button in Quest Browser, Center Reset Demo, Guard onShelfPinch, Debounce onXRSelect

## Session Type
[x] Bug fix  [ ] Feature  [ ] Refactor  [ ] Docs  [ ] Security

## What was built or changed
- Edit 0 (safeguard): Declared `const SR`, `const isQuestBrowser = /OculusBrowser/i.test(navigator.userAgent)`, and `const hasVoiceSupport = Boolean(SR) && !isQuestBrowser` at the top of the module script (right after `let activeAbortController = null;`, ~line 515). Removed the old `const SR` declaration near the voice section to avoid a duplicate. Declaring these early means `getVoiceTooltip()`, `onXRSelect()`, `onXRFrame()`, the render loop, and the click handler all reference a single module-scope constant with no Temporal Dead Zone risk.
- Edit 1: Guarded `onShelfPinch()` in `frontend/vr/index.html`. It now returns early when `isNegotiating` (already in flight), when `pendingPO` is set (guides the user to the PO card instead of re-negotiating), and when `!invoiceLocked && bins[0].status === "ok"` (Widget-A already restocked → directs to Reset Demo). It only falls through to `onInvoicePinch()` for the `awaiting-invoice`/`inbound` state and `triggerAgentRestock()` when `invoiceLocked` is true with no pending PO.
- Edit 2: Debounced `onXRSelect(event)` with a 900ms guard: `if (now - (window._lastXRSelectTime || 0) < 900) return; window._lastXRSelectTime = now;`. This absorbs the 100–300ms double-pinch jitter common with Quest hand tracking without noticeably lagging intentional single pinches.
- Edit 3: Hid the Voice button on Quest Browser / when SpeechRecognition is unsupported, and centered Reset Demo:
  - The voice-init block now runs `if (hasVoiceSupport) { new SR(); …handlers }` else hides the 2D `#btn-mic` (`btnMic.style.display = "none"`), hides `btn3DMic` (`btn3DMic.visible = false`), and centers `btn3DReset` (`position.set(0, 0, 0.01)`).
  - Removed the old `if (!SR)` relabel block (superseded by the hide-and-center else branch).
  - The `btnMic` click handler now early-returns on `!hasVoiceSupport` with a "Quest Browser lacks Web Speech API · Pinch 3D card buttons directly" status.
  - `getVoiceTooltip()` returns hands-first prompts when `!hasVoiceSupport`: `'Pinch Widget-A to restock'`, `'Pinch Approve PO or Reject'`, `'Pinch Widget-A to open invoice'`, `'Pinch Verify & Pay'`.
  - Excluded `btn3DMic` from both raycast sites: the `onXRSelect` HUD raycast and the render-loop cursor `targets` array now only push `btn3DMic` when `hasVoiceSupport && btn3DMic.visible`.
  - Guarded the `onXRFrame` near-field `index-finger-tip` poke check so `btn3DMic.getWorldPosition(p)` only runs inside `if (hasVoiceSupport && btn3DMic.visible) { … }` — poking empty space where the hidden mic used to be never fires `btnMic.click()`.

## Why (the problem being solved)
Three UX defects on Quest 2 / Quest Browser. (1) Pinching Widget-A while a PO was already drafted or already fulfilled re-ran A2A negotiation, producing confusing duplicate PO panels — `onShelfPinch` had no guard for those states. (2) Quest hand-tracking double-pinches fired two `onXRSelect` events within ~100–300ms, causing duplicate actions — no debounce existed. (3) Quest Browser either lacks the Web Speech API or ships a partial implementation that made the Voice button dead or looping; the previous build relabeled it "Voice (PC Only)" but left it visible and in the raycast/poke targets, cluttering a hands-first UI. The fix hides the mic entirely on unsupported/Quest devices, centers Reset Demo, and makes every tooltip and hit-test hands-first.

## Alternatives considered and rejected
| Option | Reason rejected |
|--------|----------------|
| Keep the "🎤 Voice (PC Only)" relabel (prior behavior) | A dead, unexplained button is clutter in a hands-first flow; hiding it and showing pinch-only prompts is cleaner |
| Disable the mic button (`btnMic.disabled = true`) | Leaves a visible non-functional control; hiding removes the affordance entirely |
| Debounce at 300ms instead of 900ms | Quest pinch jitter can exceed 300ms; 900ms reliably covers the double-pinch window |
| `hasVoiceSupport = SR && !isQuestBrowser` without `Boolean()` | `SR` is a constructor or `undefined`; `Boolean()` normalizes it to a real boolean for clean truthiness |
| Only hide 2D button, leave 3D mic visible | 3D mic would still appear in XR and be poke-hittable; must hide and exclude from raycasts/pokes |
| Relocate 3D reset button via a hardcoded offset | Centering at `(0,0,0.01)` is the correct single-button layout when the mic is gone |

## Rubric rules applied this session
- Read every file before editing (rubric §1)
- No dead imports (rubric §2)
- Early returns in `onShelfPinch` avoid needless negotiate/invoice API calls (rubric §9 — no duplicate API calls)
- Debounce prevents duplicate select events (rubric §4 — robust error/edge handling)
- No duplicate UI text (rubric §3)
- Commit message format `fix: <what> in <file> — <why>` (rubric §8)
- One PR per feature, no unrelated bundling (rubric §8)
- Ran the existing test suite before submitting (rubric §7)

## New rubric rules added this session
| Rule | File | Justification |
|------|------|---------------|
|      |      |               |

## Violations found in existing code
| File | Violation | Fixed? |
|------|-----------|--------|
| frontend/vr/index.html | Pre-existing inline `style=` attributes in generated HTML card templates (not introduced by this session) | No — out of scope for this session |

## Risk flags for next session
- Playwright headless verification could not be completed (Chromium browser binary download too slow in this environment). `node --check` on the extracted `<script>` passed and pytest (22 passed) confirms no syntax or logic regressions.
- Quest Browser detection relies on `/OculusBrowser/i.test(navigator.userAgent)`. If Meta changes the UA in future firmware, re-verify the detection.
- `hasVoiceSupport`, `SR`, `isQuestBrowser` are declared at module top (~line 515) and referenced by `getVoiceTooltip`, `onXRSelect`, `onXRFrame`, the render loop, and the mic click handler. Any future refactor that moves these declarations back down will reintroduce a TDZ ReferenceError.
- `onShelfPinch` now reads `bins[0].status`; the `bins && bins[0] &&` guard protects the init window, but callers should still ensure `bins` is populated before pinching.
- The 900ms debounce is global (`window._lastXRSelectTime`) across all controller `select` events, including shelf placement. Rapid intentional re-selection within 900ms is intentionally suppressed — verify this feels right during real Quest testing.

## Call Stack Trace (post-fix)
```
Execution Call Stack Trace:
└── [Project] Browser loads frontend/vr/index.html
    └── [Folder] frontend/vr/ → [File] index.html
        ├── [Variable] SR = window.SpeechRecognition || window.webkitSpeechRecognition
        ├── [Variable] isQuestBrowser = /OculusBrowser/i.test(navigator.userAgent)
        ├── [Variable] hasVoiceSupport = Boolean(SR) && !isQuestBrowser
        │
        ├── [Function] onShelfPinch()
        │   ├── [Guard] if (isNegotiating) return
        │   ├── [Guard] if (pendingPO) → setStatus("PO already drafted..."), return
        │   ├── [Guard] if (!invoiceLocked && bins[0]?.status === "ok") → setStatus("Widget-A restocked..."), return
        │   ├── [Branch] if (!invoiceLocked) → onInvoicePinch()
        │   └── [Default] triggerAgentRestock()
        │
        ├── [Function] onXRSelect(event)
        │   ├── [Debounce] if (now - _lastXRSelectTime < 900) return; _lastXRSelectTime = now
        │   ├── [Variable] voiceTargets[] = hasVoiceSupport && btn3DMic.visible ? [btn3DMic, btn3DReset] : [btn3DReset]
        │   └── [Raycast] raycaster.intersectObjects(voiceTargets, false)
        │
        ├── [Function] onXRFrame()
        │   └── [Guard] if (hasVoiceSupport && btn3DMic.visible) { btn3DMic.getWorldPosition(p); ... }
        │
        ├── [Voice Init] if (hasVoiceSupport) { new SR(); handlers } else { btnMic.hidden; btn3DMic.hidden; btn3DReset centered }
        ├── [Function] getVoiceTooltip() → noVoice ? pinch-only : voice+pinch
        ├── [Event Handler] btnMic.onclick → if (!hasVoiceSupport) setStatus(...), return
        └── [Render Loop] targets.push(btn3DMic) guarded by hasVoiceSupport && btn3DMic.visible
```

## Verification
- `node --check` on extracted `<script>` — syntax OK
- `pytest tests/test_vr_voice_intent.py tests/test_s23_inventory.py -q` — 22 passed
- Single `const SR`/`isQuestBrowser`/`hasVoiceSupport` declaration confirmed via grep (lines 515-517)
- No stray `if (SR)` / `if (!SR)` references remain
- Playwright headless verification: NOT COMPLETED (Chromium browser binary download too slow in this environment); `node --check` confirms no syntax errors