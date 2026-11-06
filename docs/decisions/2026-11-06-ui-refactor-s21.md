# Decision Log — 2026-11-06 — S21 UI Refactor & Cold-Start Hardening

## Session Type
[x] Feature  [x] Bug fix  [x] Refactor  [ ] Docs  [x] Security

## What was built or changed
- Removed OPERATIONAL badge, tenant selectbox (hardcoded Tenant_A), "What would you like to do" container, starter chips, and voice expanders.
- Implemented compact combined voice and text input area with dedicated `(?)` popover tooltips.
- Added docked real-time Activity Log capped at 100 entries, collapsed by default, with monospace timestamped agent steps.
- Formatted HITL Approve/Reject card with pulsing amber border (`@keyframes pulse-amber`).
- Added 1-click sample simulation and download for Warehouse and Documents.
- Added `tests/test_cold_start.py` confirming DEMO_MODE=1 cold-start in under 15 seconds.
- Cleaned dead files (`sandbox.py`, `generate_synthetic_load.py`, `health_check.py`, `terraform/main.tf`, `worker.py`, `tests/test_analytics_dashboard.py`, `tests/chaos_test.py`).
- Single-port Render configuration configured in `render.yaml` with `/ _stcore/health`.
- Generated and saved all 19 verification screenshots to `docs/ui_artifacts/`.

## Why (the problem being solved)
- Streamline user flow to operational-grade simplicity without visual clutter.
- Eliminate cold-start delays and deployment timeouts on Render.
- Verify end-to-end responsiveness and safety across mobile (390px), tablet (768px), and desktop.

## Alternatives considered and rejected
| Option | Reason rejected |
|--------|----------------|
| Floating activity log modal | Blocked main workspace and obscured chat history; docked panel is cleaner |
| Bypass fuzzy matching in test | Papered over real user-error feedback; updated assertion to expect error card |
| Multi-port Uvicorn sidecar | Caused port-binding failures and Render cold start freezes |

## Rubric rules applied this session
- Fast cold-start in DEMO_MODE=1 without external dependencies.
- No popup notifications pushing page content down (activity log docked).
- Minimalist header with pure module title.
- Zero dead imports and 100% green pytest suite.

## New rubric rules added this session
| Rule | File | Justification |
|------|------|---------------|
| Fast cold start (<15s) in DEMO_MODE=1 | docs/CODING_RUBRIC.md | Prevent Render deployment timeouts |
| Activity log docked at bottom of column | docs/CODING_RUBRIC.md | Clean layout without overlapping popups |

## Violations found in existing code
| File | Violation | Fixed? |
|------|-----------|--------|
| render.yaml | Multi-service health check conflicting on ports | Fixed |
| app.py | Startup halted on missing META_API_KEY even in DEMO_MODE | Fixed |

## Risk flags for next session
- Live Render deployment requires redeployment build to pick up new render.yaml and app.py changes.
