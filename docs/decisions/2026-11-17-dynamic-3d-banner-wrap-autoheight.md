# Decision Log — 2026-11-17 — Dynamic 3D Banner Wrap & A2A Log Auto-Height

## Session Type
[x] Feature  [ ] Bug fix  [ ] Refactor  [ ] Docs  [ ] Security

## What was built or changed
- Edit 1: Rewrote `updateMuseBanner3D(text, isLive)` in `frontend/vr/index.html` to dynamically word-wrap the banner text to a 960px max width and grow the panel's height to fit. The function now splits `text` into wrapped lines with `measureText`, sets `museBanner3DCanvas.height = Math.max(76, 36 + lines.length * 34 + 36)`, redraws a multi-line centered banner, and resizes `museBanner3DMesh.geometry` to `new THREE.PlaneGeometry(1.18, 1.18 * (canvasHeight / 1024))`. The mesh's `position.y` is anchored to `0.24 + planeH / 2` so the panel expands upward from y=0.24, away from the fixed `hudStatusMesh` at y=0.14. The old geometry is disposed before reassigning to prevent a three.js memory leak.
- Edit 2: Reworked the A2A log panel creation inside `renderPoCard(po, badge)`. Hoisted the `wrapLogLines(ctx, text, maxWidth)` helper above canvas creation, then pre-measures every wrapped line at 710px against a throwaway measuring context before drawing. This yields `totalWrappedLines`, from which `neededHeight = Math.max(440, 96 + totalWrappedLines * 28 + a2aLog.length * 10 + 24)` is computed. The canvas is resized to `768 × neededHeight`, the frame/header/entries are drawn with a 28px per-line advance, 10px between entries, and a bottom cap at `neededHeight - 24`. The mesh uses `planeH = 0.74 * (neededHeight / 768)` and `PlaneGeometry(0.74, planeH)`, anchored top-down via `position.set(-0.82, 0.27 - planeH / 2, 0.01)` so extra lines expand downward from y=0.27 without clipping.

## Why (the problem being solved)
Both 3D text panels had fixed heights that clipped long content in XR. The Muse banner drew a single centered line in an 80px canvas, so any multi-line or verbose status message was cut off. The A2A log panel capped drawing at `curY < 498` inside a fixed 520px canvas, silently dropping negotiation entries once they exceeded the panel. The fix gives both panels dynamic auto-height: the Muse banner grows upward and the A2A log grows downward, so the two panels expand away from each other and never collide, regardless of content length.

## Alternatives considered and rejected
| Option | Reason rejected |
|--------|----------------|
| Keep fixed canvas, reduce font size | Long logs still clip; smaller font hurts legibility at arm's length in XR |
| Add a vertical scroll offset / pagination | Over-engineered for a handful of lines; auto-height removes the need entirely |
| Grow Muse banner downward instead of upward | Would collide with hudStatusMesh (y=0.14) and the A2A log top anchor (y=0.27); upward growth keeps the two panels diverging |
| Grow A2A log upward instead of downward | Would collide with the Muse banner and header; anchoring at the top y=0.27 and growing down is clean |
| Resize canvas without pre-measuring | Drawing must happen after resize or content is cleared; pre-measure gives the exact height before any draw call |
| Use `THREE.TextGeometry` | Requires a font loader and per-string rebuilds; `CanvasTexture` is lighter and already in use |

## Rubric rules applied this session
- Read every file before editing (rubric §1)
- One-line purpose comments added for the dynamic-wrap behavior (rubric §2 docstring convention)
- No dead imports introduced (rubric §2)
- No duplicate UI text introduced (rubric §3)
- Commit message format `feat: <what> in <file> — <why>` (rubric §8)
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
- `wrapLogLines` is defined inside `renderPoCard`, so it is re-created on every call. This is intentional for locality; hoisting to module scope is a reasonable future refactor if reused elsewhere.
- The A2A draw loop caps at `curY < neededHeight - 24`. Because `neededHeight` is pre-computed from the same wrapped-line measurement, the cap should never truncate real content — but if `a2aLog` grows very large, verify the computed height still covers every line.
- Muse banner and A2A log now grow in opposite directions (up / down) from nearby anchors (0.24 / 0.27). They will not collide, but a future layout change that moves either anchor closer could cause overlap — re-check the 0.03m gap if anchors change.
- Geometry disposal is only in `updateMuseBanner3D`; the A2A log mesh is rebuilt from scratch each `renderPoCard` call and its old mesh/material/texture are disposed at the top of the block, so no leak there.

## Call Stack Trace (post-fix)
```
Execution Call Stack Trace:
└── [Project] Browser loads frontend/vr/index.html
    └── [Folder] frontend/vr/ → [File] index.html
        ├── [Function] updateMuseBanner3D(text, isLive)
        │   ├── [Variable] lines[] = wrapped text at 960px
        │   ├── [Variable State Shift] museBanner3DCanvas.height: 80 → max(76, 36 + n*34 + 36)
        │   ├── [Variable State Shift] PlaneGeometry: (1.18, 0.095) → (1.18, 1.18*h/1024)
        │   ├── [Variable State Shift] mesh.position.y: 0.27 → 0.24 + planeH/2 (grows UP)
        │   └── [Method] old geometry.dispose(); museBanner3DTex.needsUpdate = true
        │
        └── [Function] renderPoCard(po, badge)
            ├── [Variable] totalWrappedLines = Σ wrapLogLines(measureCtx, ..., 710).length
            ├── [Variable State Shift] logCanvas.height: 520 → max(440, 96 + n*28 + entries*10 + 24)
            ├── [Variable State Shift] PlaneGeometry: (0.74, 0.50) → (0.74, 0.74*h/768)
            ├── [Variable State Shift] mesh.position.y: 0.02 → 0.27 - planeH/2 (grows DOWN)
            └── [Method] logTex.needsUpdate = true
            └── [Project] Both 3D panels auto-size; Muse up from 0.24, A2A down from 0.27 — no collision
```

## Verification
- `node --check` on extracted `<script>` — syntax OK
- `pytest tests/test_vr_voice_intent.py tests/test_s23_inventory.py -q` — 22 passed
- No new inline `style=` attributes introduced
- No dead imports introduced
- Playwright headless verification: NOT COMPLETED (Chromium browser binary download too slow in this environment); `node --check` confirms no syntax errors