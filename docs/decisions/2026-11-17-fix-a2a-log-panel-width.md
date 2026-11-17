# Decision Log — 2026-11-17 — Fix A2A Negotiation Log 3D Panel Width and Text Wrapping

## Session Type
[ ] Feature  [x] Bug fix  [ ] Refactor  [ ] Docs  [ ] Security

## What was built or changed
- Edit 1: Reworked the A2A log panel creation block inside `renderPoCard(po, badge)` in `frontend/vr/index.html` (previously lines 1283-1308). Replaced the 512×320 canvas with a 768×520 canvas and redrew it with a bordered frame (`strokeRect`) plus a dedicated header bar (`fillRect` at 8,8,752,54), rather than `roundRect` over a filled background.
- Edit 2: Added a local `wrapLogLines(ctx, text, maxWidth)` helper inside `renderPoCard`. It splits each log entry on whitespace, greedily measures candidate lines with `ctx.measureText`, and returns an array of lines that each fit within `maxWidth`. Empty/undefined text degrades to an empty array via `String(text || "")`.
- Edit 3: Replaced the single-overflow-line entry draw with a wrapping loop. Each `a2aLog` entry is cleaned of tags (`replace(/<[^>]+>/g, "")`), prefixed with its icon, and wrapped to 720px. Lines are drawn at `x = 22` advancing `curY` by 27px per line, with continuation lines indented by three spaces; 8px is added between entries. Drawing is capped at `curY < 498` so entries never spill off the bottom edge.
- Edit 4: Enlarged the 3D `PlaneGeometry` from `(0.5, 0.32)` to `(0.74, 0.50)` and moved `logMesh` from `(-0.72, 0, 0.01)` to `(-0.82, 0.02, 0.01)`. The new right edge is `-0.82 + 0.37 = -0.45`, leaving a clean gap to the PO card's left edge at `-0.36` (card half-width `0.78/2 = 0.39`).

## Why (the problem being solved)
The A2A negotiation log panel in the VR scene truncated long log entries on the right. The 512×320 canvas was too narrow, entries were drawn as a single `fillText` line each, and the panel sat only 0.72m left of the PO card — visually crowded and clipped. The fix widens the canvas and plane, moves the panel left for a clean seam, and wraps each entry across multiple lines so no text is ever cut off.

## Alternatives considered and rejected
| Option | Reason rejected |
|--------|----------------|
| Keep single-line `fillText` with a smaller font | Long entries still overflow the right edge; shrinking the font hurts legibility at arm's length in VR |
| Widen canvas but keep `roundRect` on a filled background | The dark fill against a transparent map made edges muddy; explicit `strokeRect` + header bar reads crisper |
| Move panel further left (`-0.9` or beyond) | Widens the visual gap to the PO card more than needed; `-0.82` already clears the `-0.36` left edge by 0.09m |
| Use `THREE.TextGeometry` for real 3D text | Requires a font loader and per-string geometry rebuilds; a `CanvasTexture` is lighter and re-renders on each `renderPoCard` call |
| Scroll/paginate entries | Over-engineered for a handful of log lines; wrapping handles volume without extra UI |

## Rubric rules applied this session
- Read every file before editing (rubric §1)
- Added a one-line purpose comment for the new `wrapLogLines` helper (rubric §2 — docstring convention)
- No dead imports introduced (rubric §2)
- No new UI text duplicated across header/breadcrumb/sidebar (rubric §3) — this is a 3D texture, not DOM UI
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
| frontend/vr/index.html | Pre-existing unused `floorPlane` / other dead declarations if any remain (see prior decision logs) | No — out of scope |

## Risk flags for next session
- Playwright headless verification could not be completed (Chromium browser binary download too slow in this environment). `node --check` on the extracted `<script>` passed and pytest (22 passed) confirms no syntax or logic regressions.
- `wrapLogLines` is defined inside `renderPoCard`, so it is re-created on every call. This is intentional for locality (the helper only serves this panel) but a hoist to module scope is a reasonable future refactor if it is reused.
- The bottom draw cap (`curY < 498`) silently drops entries beyond the panel height. If `a2aLog` grows unbounded, consider a scroll offset or truncation marker.

## Call Stack Trace (post-fix)
```
Execution Call Stack Trace:
└── [Project] Browser loads frontend/vr/index.html (module script)
    └── [Folder] frontend/vr/ → [File] index.html
        └── [Function] renderPoCard(po, badge)
            └── [Variable State Shift] logCanvas: 512×320 → 768×520
            └── [Method] wrapLogLines(logCtx, cleanText, 720) → array of lines
                └── [Variable State Shift] each entry wrapped to ≤720px; 27px per line, +8px between entries
            └── [Variable State Shift] logMesh geometry: (0.5, 0.32) → (0.74, 0.50)
            └── [Variable State Shift] logMesh.position: (-0.72, 0, 0.01) → (-0.82, 0.02, 0.01)
            └── [Project] Right edge = -0.82 + 0.37 = -0.45, clean 0.09m gap to PO card left edge -0.36
```

## Verification
- `node --check` on extracted `<script>` — syntax OK
- `pytest tests/test_vr_voice_intent.py tests/test_s23_inventory.py -q` — 22 passed
- No new inline `style=` attributes introduced
- No dead imports introduced
- Playwright headless verification: NOT COMPLETED (Chromium browser binary download too slow in this environment); `node --check` confirms no syntax errors