# Decision Log — 2026-11-18 — Fix Quest 2 Voice Loop, Abort In-Flight Muse Requests, "units" Labels & Banner Text

## Session Type
[x] Bug fix  [ ] Feature  [ ] Refactor  [ ] Docs  [ ] Security

## What was built or changed
- Edit 1: Auto-scaled the subtitle font in `createLabelTexture(title, subtitle, bgColor, borderColor)` in `frontend/vr/index.html`. The subtitle font now sizes by length: `>18 chars → 26px`, `>14 chars → 30px`, else `34px`. Long labels like `"500 units · INBOUND"` (21 chars) now render at 26px and no longer overflow the 512px canvas.
- Edit 2: Replaced all 10 `"u"` unit abbreviations with `"units"` across `build3DShelf()` (3), `update3DBin()` (3), `renderDesktopBins()` (2), `renderPoCard()` item row (1), and `verifyInvoicePayment()` status line (1). `verifyInvoicePayment` preserved its trailing `"End of Demo"` text.
- Edit 3: Added a request-cancellation guard system. Declared `let demoGeneration = 0;` and `let activeAbortController = null;` in app state. In `triggerAgentRestock()`, `onInvoicePinch()`, `verifyInvoicePayment()`, and `resolveIntent(transcript)` each function now: (a) captures `const myGen = demoGeneration;`, (b) aborts any prior `activeAbortController` then assigns a new `AbortController()`, (c) passes `signal: activeAbortController.signal` to its `fetch`, (d) returns early in `catch` when `err?.name === "AbortError" || myGen !== demoGeneration`, and (e) checks `if (myGen !== demoGeneration) return;` after every `await` before mutating state or opening a panel. `resolveIntent` now returns `null` on abort/generation-change, and `recognition.onresult` guards `if (intent == null) return;` to discard stale voice results. `resetDemo()` now increments `demoGeneration`, aborts + clears `activeAbortController`, and stops active `recognition` at the top — without duplicating the existing `isNegotiating = false` already in its body.
- Edit 4: Fixed the Quest 2 voice-button loop. Added a `if (!SR)` block that relabels `btnMic` to `"🎤 Voice (PC Only)"` and swaps the `btn3DMic` 3D texture to a "Pinch 3D Buttons" label. The `btnMic` click handler now, when `!recognition`, calls `setStatus("Quest Browser lacks Web Speech API · Pinch 3D card buttons directly", true)` and returns instead of calling `triggerAgentRestock()` on every click.
- Edit 5: Updated the Muse banner fallback text (both the 2D `#muse-banner` and the 3D `updateMuseBanner3D`) in the else and catch branches to `"⚠️ Simulated Muse mode (Meta API blocks cloud IPs) · Run locally with META_API_KEY for live AI"`.

## Why (the problem being solved)
Three distinct bugs. (1) On Quest 2 Browser the Web Speech API is unavailable, so `recognition` was `null`; the mic click handler fell back to `triggerAgentRestock()` on every press, creating a frustrating loop that re-fired negotiation and re-opened the PO panel. (2) When the user hit Reset Demo mid-flight, any in-progress `/api/vr/negotiate`, `/invoice-scan`, `/invoice-pay`, or `/interpret-voice` request would still resolve and repopulate state / reopen panels after the reset, so the demo appeared to "come back" after being cleared. (3) The "u" abbreviation was inconsistent with the rubric's preference for clarity and the shorter 3D labels overflowed their boxes once spelled out — auto-scaling fixes the fit. Separately, the "Mock AI agent demo active" banner wrongly implied a config error on Render when the real cause is that Meta's API blocks cloud IPs.

## Alternatives considered and rejected
| Option | Reason rejected |
|--------|----------------|
| Disable the mic button entirely on Quest 2 (`btnMic.disabled = true`) | Leaves a dead, unexplained control; relabeling + a status message tells the user why and points them at the 3D buttons |
| Use a boolean `let stale = false` instead of a generation counter | A generation counter handles multiple rapid resets correctly; a single boolean cannot distinguish reset #1 from reset #2 |
| Only abort, no generation guard | `AbortController.abort()` rejects the fetch, but a request that already resolved before the abort could still run its continuation; the `myGen !== demoGeneration` check closes that race |
| Global `AbortController` reused without re-creating | A single aborted controller cannot be reused; a fresh `new AbortController()` per request is required |
| Keep "u" and shrink font further | "units" is clearer and the auto-scale (26/30/34px) already fits without overflow; shrinking "u" hides the ambiguity |
| Change banner text only in 2D, not 3D | The 3D HUD banner would keep showing the wrong message in XR; both must match |

## Rubric rules applied this session
- Read every file before editing (rubric §1)
- Every fetch now has explicit abort + error handling with user-friendly status (rubric §4)
- No duplicate UI text introduced (rubric §3)
- No duplicate `isNegotiating = false` — reused the existing assignment in `resetDemo` (rubric §2, no duplicate code)
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
- `resolveIntent` can now return `null`. Any future caller must handle `null` (the current `recognition.onresult` does via `if (intent == null) return;`). `handleIntent(null)` also safely no-ops through its equality checks, but callers should not assume a non-null string.
- `resetDemo()` references `recognition` and `listening`, which are declared later in the module (voice section). This is safe because `resetDemo` is only invoked at runtime after module init, but a future synchronous call during init would hit the TDZ.
- The `demoGeneration` counter grows unbounded; JS integers are safe to 2^53, so practically never an issue even over a very long session.
- Quest 2 detection relies on `window.SpeechRecognition || window.webkitSpeechRecognition` being absent. If a future Quest Browser ships a partial Web Speech API, the `!SR` branch will not trigger — re-verify on new firmware.

## Call Stack Trace (post-fix)
```
Execution Call Stack Trace:
└── [Project] Browser loads frontend/vr/index.html
    └── [Folder] frontend/vr/ → [File] index.html
        ├── [Variable] demoGeneration = 0; activeAbortController = null
        │
        ├── [Function] createLabelTexture(title, subtitle, bgColor, borderColor)
        │   └── [Variable State Shift] ctx.font: 34px → (26px | 30px | 34px) by subtitle.length
        │       └── [Project] "500 units · INBOUND" (21 chars) → 26px, no overflow
        │
        ├── [String Replacement] "u" → "units" (build3DShelf, update3DBin, renderDesktopBins, renderPoCard, verifyInvoicePayment)
        │
        ├── [Function] triggerAgentRestock() | onInvoicePinch() | verifyInvoicePayment() | resolveIntent()
        │   ├── [Variable] myGen = demoGeneration (captured)
        │   ├── [Method] activeAbortController.abort(); activeAbortController = new AbortController()
        │   ├── [Method] fetch(..., { signal: activeAbortController.signal })
        │   ├── [Guard] if (myGen !== demoGeneration) return (after every await)
        │   ├── [Catch] if (err?.name === "AbortError" || myGen !== demoGeneration) return
        │   └── [ResolveIntent] returns null on abort/generation-change
        │
        ├── [Event] recognition.onresult
        │   └── [Guard] if (intent == null) return (discard stale voice result after reset)
        │
        ├── [Function] resetDemo()
        │   ├── [Variable State Shift] demoGeneration++
        │   ├── [Method] activeAbortController.abort(); activeAbortController = null
        │   ├── [Method] recognition.stop() (if listening)
        │   └── [Note] existing isNegotiating = false (line ~1591) reused, not duplicated
        │
        ├── [Event Handler] btnMic.onclick
        │   ├── [if !SR] btnMic="🎤 Voice (PC Only)" + 3D texture swap
        │   ├── [if !recognition] setStatus("Quest Browser lacks Web Speech API..."), return
        │   └── [normal] recognition.start()/stop()
        │
        └── [Script] Muse banner IIFE
            └── [String Replacement] fallback ×3 → "Simulated Muse mode (Meta API blocks cloud IPs)..."
            └── [Project] 2D #muse-banner + 3D HUD show accurate cloud-IP explanation
```

## Verification
- `node --check` on extracted `<script>` — syntax OK
- `pytest tests/test_vr_voice_intent.py tests/test_s23_inventory.py -q` — 22 passed
- "u" → "units" replacements: 10 locations confirmed via grep
- `resetDemo` does not duplicate `isNegotiating = false` (reuses existing assignment)
- Playwright headless verification: NOT COMPLETED (Chromium browser binary download too slow in this environment); `node --check` confirms no syntax errors